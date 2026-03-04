import numpy as np
from collections import defaultdict
import unicodedata, re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

import json
import logging
_logger = logging.getLogger(__name__)


MODEL_NAME = 'VoVanPhuc/sup-SimCSE-VietNamese-phobert-base'
PRICE_DIFF = 0.15

def normalize(text):
    text = text.lower()
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_model(model_name=False):
    model_name = model_name or MODEL_NAME
    model = SentenceTransformer(model_name)
    return model

def encode(source_items, model_name=False, is_normalize=True, np_array=False, model=False):
    if not model:
        model = get_model(model_name)

    source_names = [normalize(item) for item in source_items] if is_normalize else source_items
    source_vectors = model.encode(source_names, convert_to_tensor=False, show_progress_bar=False)

    source_vectors = np.array(source_vectors) if np_array else source_vectors

    return source_vectors

def get_vector_json(name):
    if not name: return ''
    return json.dumps(encode([name], np_array=False)[0].tolist())

def generate_ai_vector(products, check_generated=True, name_field='name', auto_commit=False):
    has_names = products.filtered(lambda x: x[name_field] and (not check_generated or not x.ai_vector) )
    if not has_names: return
    
    _logger.info('Bắt đầu vector hoá %s phần tử' % len(has_names))
    ai_vectors = get_vectors_json(has_names.mapped(name_field))
    i = 0
    for rec in has_names:
        rec.ai_vector = ai_vectors[i]
        i += 1
    _logger.info('Hoàn tất vector hoá %s phần tử' % len(has_names))

    if auto_commit: products.env.cr.commit()

def get_vectors_json(names):
    if not names:
        return []

    # Gọi encode nhiều name cùng lúc
    vectors = encode(names, np_array=False)

    # Chuyển từng vector thành JSON string
    return [json.dumps(vec.tolist()) for vec in vectors]

def get_candidate(original_json_vector, candidate_json_vectors):
    original_vector = np.array(json.loads(original_json_vector)).reshape(1, -1)
    compare_vectors = np.array([json.loads(compare_vector) for compare_vector in candidate_json_vectors])

    scores = cosine_similarity(original_vector, compare_vectors)[0]
    max_score = 0
    max_index = 0
    for index in range(len(scores)):
        score = scores[index]
        if score > max_score:
            max_score = score
            max_index = index

    return max_index, max_score

def get_candidate_scores(original_name, candidate_names):
    """
    Hàm trả về độ tương hợp của một dãy các string candidate_names so với string original_name
    Lưu ý: string truyền vào không được rỗng, rỗng sẽ có exception
    """
    original_json_vector = encode([original_name])[0]
    compare_vectors = encode(candidate_names)
    return cosine_similarity(original_json_vector.reshape(1, -1), compare_vectors)[0]

# def encode_in_batches(model, names, batch_size=1024, num_workers=4, normalize_embeddings=True):
def encode_in_batches(model, names, batch_size=5000):
    vectors = []
    total = len(names)
    for i in range(0, total, batch_size):
        batch = names[i:i + batch_size]
        _logger.info("Đang xử lý batch %d ~ %d/%d", i, i + len(batch), total)
        batch_vectors = model.encode(
            batch,
            convert_to_tensor=False,
            show_progress_bar=False,
            # batch_size=64,
            # num_workers=num_workers,
            # normalize_embeddings=normalize_embeddings,
        )
        vectors.extend(batch_vectors)
    return np.array(vectors)


def _find_similar_for_batch(source_items_batch, source_vectors_batch, target_items, target_vectors, target_prices, initial_target_qtys, price_diff, check_stock, check_price, get_number):
    """
    Hàm worker này xử lý một lô (batch) của source_items.
    Nó nhận vào dữ liệu của target đã được tính toán trước để tăng hiệu suất.
    """
    _logger.info("Tính toán ma trận tương đồng cho lô %d x %d sản phẩm...", len(source_items_batch), len(target_items))
    similarity_matrix = cosine_similarity(source_vectors_batch, target_vectors)
    _logger.info("Hoàn thành ma trận tương đồng cho lô.")

    result_batch = {}
    source_prices_batch = np.array([item['price'] for item in source_items_batch])
    source_qtys_batch = np.array([item['qty'] for item in source_items_batch])
    
    # Rất quan trọng: Phải copy lượng tồn kho cho mỗi lô để việc cập nhật không ảnh hưởng đến lô sau.
    updatable_target_qtys = initial_target_qtys.copy()

    for i in range(len(source_items_batch)):
        similarities_for_one_source = similarity_matrix[i].copy()

        # Lọc theo giá (vectorized)
        if check_price:
            min_price = source_prices_batch[i] * (1 - price_diff)
            max_price = source_prices_batch[i] * (1 + price_diff)
            price_mask = (target_prices >= min_price) & (target_prices <= max_price)
            similarities_for_one_source[~price_mask] = -1

        # Lọc theo tồn kho (vectorized)
        if check_stock:
            stock_mask = updatable_target_qtys >= source_qtys_batch[i]
            similarities_for_one_source[~stock_mask] = -1

        # Tìm kết quả tốt nhất
        sorted_target_indices = np.argsort(similarities_for_one_source)[::-1]
        
        valid_matches = []
        for target_idx in sorted_target_indices:
            score = similarities_for_one_source[target_idx]
            if score > -1:
                valid_matches.append({'match_index': target_idx, 'score': score})
                if len(valid_matches) >= get_number:
                    break
            else:
                break

        # Lưu kết quả và cập nhật tồn kho
        if valid_matches:
            best_match = valid_matches[0]
            result_item = {'match_index': best_match['match_index'], 'score': best_match['score']}
            for j, match in enumerate(valid_matches[1:], start=1):
                result_item[f'match_index_{j}'] = match['match_index']
                result_item[f'score_{j}'] = match['score']
            result_batch[i] = result_item
            
            if check_stock:
                matched_target_idx = best_match['match_index']
                updatable_target_qtys[matched_target_idx] -= source_qtys_batch[i]
        else:
            result_batch[i] = {'match_index': -1, 'score': 0}
            
    return result_batch

def find_similar_product(source_items, target_items=False, model_name=False, price_diff=None, check_stock=False, check_price=True, get_number=1, batch_size=1000):
    """
    Hàm chính để tìm sản phẩm tương tự, hỗ trợ xử lý theo từng lô (batch)
    để tránh tràn bộ nhớ với dữ liệu lớn.
    """
    if not source_items:
        return {}
    if price_diff is None:
        price_diff = PRICE_DIFF
    if target_items is False:
        target_items = source_items

    # --- CHUẨN BỊ DỮ LIỆU TARGET MỘT LẦN DUY NHẤT ---
    # Việc này rất quan trọng để không phải lặp lại trong mỗi vòng lặp lô
    _logger.info("Chuẩn bị dữ liệu cho %d sản phẩm đích...", len(target_items))
    target_vectors = np.array([json.loads(item['ai_vector']) for item in target_items])
    target_prices = np.array([item['price'] for item in target_items])
    initial_target_qtys = np.array([item.get('qty_available', 0) for item in target_items], dtype=np.float32)
    _logger.info("Chuẩn bị xong dữ liệu đích.")

    all_results = {}
    total_sources = len(source_items)

    # --- VÒNG LẶP CHIA LÔ ---
    for i in range(0, total_sources, batch_size):
        # Lấy ra một lô sản phẩm nguồn
        source_items_batch = source_items[i : i + batch_size]
        _logger.info("Đang xử lý lô sản phẩm nguồn từ %d đến %d / %d...", i, i + len(source_items_batch), total_sources)
        
        # Chuẩn bị vector cho lô hiện tại
        source_vectors_batch = np.array([json.loads(item['ai_vector']) for item in source_items_batch])
        
        # Gọi hàm worker để xử lý cho lô này
        batch_result = _find_similar_for_batch(
            source_items_batch, source_vectors_batch,
            target_items, target_vectors, target_prices, initial_target_qtys,
            price_diff, check_stock, check_price, get_number
        )
        
        # Gộp kết quả của lô vào kết quả tổng
        # Cần điều chỉnh lại index cho đúng với index gốc
        for batch_idx, result_item in batch_result.items():
            original_idx = i + batch_idx
            all_results[original_idx] = result_item

    _logger.info("Hoàn tất xử lý tất cả các lô.")
    return all_results

# def find_similar_product(source_items, target_items=False, model_name=False, price_diff=None, check_stock=False, check_price=True, get_number=1):
#     """
#     Đầu vào: danh sách các dict.
#     """
#     if not source_items:
#         return {}
#     if price_diff is None:
#         price_diff = PRICE_DIFF

#     # model_name = model_name or MODEL_NAME
#     # _logger.info('Load model %s', model_name)
#     # model = SentenceTransformer(model_name)
#     # _logger.info('Load xong model %s', model_name)

#     # _logger.info('Vector hoá danh sách 1, %s phần tử', len(source_items))

#     # source_names = [normalize(item['name']) for item in source_items]
#     # source_vectors = encode_in_batches(model, source_names)

#     # if target_items:
#     #     _logger.info('Vector hoá danh sách 2, %s phần tử', len(target_items))
#     #     target_names = [normalize(item['name']) for item in target_items]
#     #     target_vetors = encode_in_batches(model, target_names)
#     # else:
#     #     target_names = source_names
#     #     target_vetors = source_vectors

#     # _logger.info('Đã vector xong')

#     source_vectors = np.array([json.loads(item['ai_vector']) for item in source_items])

#     if target_items:
#         _logger.info('Lấy vector có sẵn từ danh sách 2, %s phần tử', len(target_items))
#         # Trực tiếp lấy 'ai_vector' từ mỗi item
#         target_vetors = np.array([json.loads(item['ai_vector']) for item in target_items])
#     else:
#         # Nếu không có target_items, tự so sánh với chính nó
#         target_vetors = source_vectors

#     result = {}
#     stock_use = defaultdict(float)

#     for source_index in range(len(source_vectors)):
#         source_item = source_items[source_index]
#         source_vector = source_vectors[source_index]

#         _logger.info('Xử lý item %s/%s %s', source_index, len(source_vectors), source_item['name'])

#         target_indexs = []
#         match_result = False
#         for target_index in range(len(target_items)):
#             price_ok = True
#             if check_price:
#                 source_price = source_item['price']
#                 min_price = source_price * (1 - price_diff)
#                 max_price = source_price * (1 + price_diff)
#                 target_price = target_items[target_index]['price']
#                 price_ok = target_price >= min_price and target_price <= max_price
            
#             stock_ok = True
#             if check_stock:
#                 stock_ok = target_items[target_index]['qty_available'] >= source_items[source_index]['qty'] + stock_use.get(target_index, 0)
            
#             if price_ok and stock_ok:
#                 target_indexs.append(target_index)

#         match_result = None
#         match_result_all = []
#         if target_indexs:
#             compare_vectors = target_vetors[target_indexs]
#             similarities = cosine_similarity(source_vector.reshape(1, -1), compare_vectors)[0]

#             match_result_all = sorted(zip(similarities, target_indexs), key=lambda x: -x[0])
#             if match_result_all:
#                 match_result = match_result_all[0]

#             if match_result:
#                 _logger.info('Kết quả match: source: %s, match: %s, tương hợp: %s', source_item['name'], target_items[match_result[1]]['name'], match_result[0])

#         if match_result and check_stock:
#             stock_use[match_result[1]] += source_items[source_index]['qty']

#         result_more = {}
#         for i in range(1,  min(get_number, len(match_result_all)) ):
#             result_more.update({
#                 f'match_index_{i}': match_result_all[i][1],
#                 f'score_{i}': match_result_all[i][0],
#             })

#         result[source_index] = {
#             'match_index': match_result[1] if match_result else -1,
#             'score': match_result[0] if match_result else 0,
#             ** result_more
#         }

#     return result


def group_similar_product(source_items, model_name=False, score=0.75, scrorex=2, batch_size=1000):
    if not source_items:
        return {}

    source_vectors = np.array([json.loads(item['ai_vector']) for item in source_items])

    grouped_score = defaultdict(set)
    N = len(source_items)
    for start_i in range(0, N, batch_size):
        _logger.info(f'B1. Xử lý score item {start_i}:{start_i+batch_size}/{len(source_vectors)}')
        end_i = min(start_i + batch_size, N)

        batch_source_vectors = source_vectors[start_i:end_i]
        target_vectors = source_vectors[start_i:]
        batch_similarities = cosine_similarity(batch_source_vectors, target_vectors)

        for relative_i, i in enumerate(range(start_i, end_i)):
            # relative_i là chỉ số của vector trong batch_source_vectors
            # i là chỉ số gốc của vector trong source_vectors (0 đến 75999)
        
            # current_sims là mảng 1D độ dài N (similarity(i, j) với j = 0..N-1)
            current_sims = batch_similarities[relative_i]
            for j in range(relative_i+1, len(target_vectors)):
                if current_sims[j] >= score and current_sims[j] < scrorex:
                    grouped_score[i].add(start_i + j)

    grouped = {}
    grouped_map = {}
    for source_index in range(len(source_vectors)):
        _logger.info('B cuối. Phân nhóm cho %s / %s', source_index, len(source_vectors))
        if source_index in grouped_map: 
            _logger.info('bỏ qua do đã phân nhóm')
            continue

        grouped_map[source_index] = source_index
        grouped[source_index] = [source_index]

        # for target_index in range(source_index+1, len(source_vectors)):
        for target_index in grouped_score[source_index]:
            if target_index in grouped_map: continue

            if all(index in grouped_score[target_index] or target_index in grouped_score[index] for index in grouped[source_index]):
                grouped_map[target_index] = source_index
                grouped[source_index].append(target_index)

    result = {}
    for source_index in range(len(source_vectors)):
        result[source_index] = {
            'match_index': grouped_map[source_index],
            'score': score,
        }

    return result

def get_similarity(source_items, target_items):

    target_vectors = np.array([item['ai_vector'] for item in target_items])
    source_vectors = np.array([item['ai_vector'] for item in source_items])
    
    result = cosine_similarity(source_vectors, target_vectors)

    similarity_maps = defaultdict(list)
    for i in range(len(result)):
        for j in range(len(result[i])):
            similarity_maps[source_items[i]['id']].append({'product_id': target_items[j]['id'], 'similarity': result[i][j]})

    # sắp xếp giảm dần theo similarity
    for product_id, sims in similarity_maps.items():
        similarity_maps[product_id] = sorted(sims, key=lambda x: x['similarity'], reverse=True)

    return similarity_maps










