# Map sản phẩm với Danh mục
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report

import re
from collections import defaultdict


import logging
_logger = logging.getLogger(__name__)

TOP_N_KEYWORDS = 200 # Số lượng từ khóa hàng đầu cần lấy cho mỗi danh mục

# Danh sách các từ dừng (stop words) phổ biến trong tiếng Việt
VIETNAMESE_STOP_WORDS = [
    'và', 'của', 'là', 'các', 'một', 'cho', 'rất', 'được', 'có', 'không', 'để',
    'khi', 'thì', 'tại', 'bị', 'ở', 'đã', 'về', 'này', 'khác', 'như', 'với',
    'làm', 'đến', 'trong', 'trên', 'dưới', 'cũng', 'sẽ', 'đang', 'đó', 'nó',
    'từ', 'sản phẩm', 'chất lượng', 'cao cấp', 'chính hãng', 'giá rẻ'
]

def preprocess_text(text):
    """Hàm tiền xử lý văn bản: chuyển chữ thường, bỏ ký tự đặc biệt."""
    # Chuyển thành chữ thường
    if not text: 
        return ''
    text = text.lower()
    # Xóa các ký tự không phải là chữ cái, số, hoặc khoảng trắng
    text = re.sub(r'[^\w\s]', '', text)
    return text

def extract_keywords_from_data(env, training_datas):
    print('xxxxxx1')
    df = pd.DataFrame(training_datas)
    # df.rename(columns={'product_name': 'ten_san_pham', 'category_name': 'ten_danh_muc'}, inplace=True)
    print('xxxxxx')
    # print(str(training_datas))
    products_by_category = df.groupby('category_code')['product_name'].apply(lambda x: ' '.join(map(preprocess_text, x)))
    print('xxxxxx2')


    # Danh sách các danh mục và các văn bản tương ứng
    categories = products_by_category.index.tolist()
    products = products_by_category.tolist()

    # Áp dụng thuật toán TF-IDF
    if len(categories) > 1:
        vectorizer = TfidfVectorizer(
            stop_words=VIETNAMESE_STOP_WORDS,
            ngram_range=(1, 2), # Xem xét cả từ đơn và cụm 2 từ
            max_df=0.8, # Bỏ qua các từ xuất hiện trong hơn 80% danh mục
            min_df=1 # Bỏ qua các từ xuất hiện ít hơn 2 lần
        )
    else:
        vectorizer = TfidfVectorizer(
            stop_words=VIETNAMESE_STOP_WORDS,
            ngram_range=(1, 2), # Xem xét cả từ đơn và cụm 2 từ
            # max_df=0.8, # Bỏ qua các từ xuất hiện trong hơn 80% danh mục
            min_df=1, # Bỏ qua các từ xuất hiện ít hơn 2 lần
            use_idf=False,
        )

    tfidf_matrix = vectorizer.fit_transform(products)

    # Lấy danh sách các từ/cụm từ (features)
    feature_names = vectorizer.get_feature_names_out()

    # 4. Trích xuất và lưu trữ từ khóa cho mỗi danh mục
    keywords_by_category = {}
    print("Đang trích xuất và sắp xếp các từ khóa hàng đầu...")
    for i, category in enumerate(categories):
        # Lấy vector TF-IDF của danh mục thứ i
        row = tfidf_matrix.getrow(i).toarray().flatten()
        
        product_category = env['product.category.training'].search([('category_code', '=', category)])
        if not product_category:
            raise UserError('Không tìm thấy danh mục')

        keyword_values = [(5, 0, 0)]

        # Ghép feature_names và điểm số tương ứng, sau đó sắp xếp
        scores_with_features = zip(feature_names, row)
        for word, score in scores_with_features:
            if score <= 0: continue
            keyword_values.append((0, 0, {'name': word, 'score': score}))

        product_category.write({'keyword_ids': keyword_values})

def classify_product(env, categories, products, update_field_name=False):
    # categories = env['product.category.training'].search([])
    keyword_brain = {}
    category_codes = {}

    for category in categories:
        category_codes[category.category_code] = category
        keyword_brain[category.category_code] = {}
        for keyword in category.keyword_ids:
            keyword_brain[category.category_code][keyword.name] = keyword.score

    # Lấy danh sách tất cả các danh mục từ 'bộ não'
    all_categories = keyword_brain.keys()

    all_category_scores = {}

    for product in products:
        _logger.info('Ghép danh mục cho sản phẩm %s' % product.name)
        best_category = env.ref('ttb_product.product_category_unclassified')
        # 1. Tiền xử lý tên sản phẩm
        product_name = preprocess_text(product.name)
        words = product_name.split()

        # 2. Tạo tokens (từ đơn và cụm 2 từ) giống như lúc tạo từ khóa
        unigrams = words
        bigrams = [' '.join(words[i:i+2]) for i in range(len(words)-1)]
        tokens = unigrams + bigrams

        # 3. Tính điểm cho mỗi danh mục
        category_scores = defaultdict(float)
        category_scores_detail = defaultdict(dict)

        for category in all_categories:
            for token in tokens:
                # Nếu token là một từ khóa của danh mục này, cộng điểm của nó
                if token in keyword_brain[category]:
                    category_scores[category] += keyword_brain[category][token]
                    category_scores_detail[category][token] = keyword_brain[category][token]

        # 4. Tìm danh mục có điểm cao nhất
        if category_scores: # Nếu không có từ khóa nào khớp
            best_category = max(category_scores, key=category_scores.get)
            best_category = category_codes[best_category]
        if update_field_name and not product[update_field_name]:
            product.write({update_field_name: best_category.id})
        all_category_scores[product.id] = {
            'sum': category_scores,
            'detail': category_scores_detail,
        }

    return all_category_scores


def train_model(training_data):
    """
    Huấn luyện mô hình từ dữ liệu Odoo.
    :param training_data: List of dicts [{'product_name': '...', 'category_code': '...'}]
    :return: (pipeline, accuracy_train, accuracy_test, report)
    """
    if not training_data:
        return None, 0, 0, "Không có dữ liệu huấn luyện."

    df = pd.DataFrame(training_data)
    df.dropna(subset=['product_name', 'category_code'], inplace=True)
    
    if df.empty:
        return None, 0, 0, "Dữ liệu huấn luyện rỗng sau khi làm sạch."

    df['cleaned_name'] = df['product_name'].apply(preprocess_text)
    
    X = df['cleaned_name']
    y = df['category_code']
    
    # Stratify=y rất quan trọng cho dữ liệu không cân bằng
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)

    # Dùng LogisticRegression để có thể lấy xác suất (predict_proba)
    model_pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            # stop_words=VIETNAMESE_STOP_WORDS,
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.8
        )),
        ('clf', LogisticRegression(random_state=42, max_iter=1000, class_weight='balanced'))
    ])

    model_pipeline.fit(X_train, y_train)

    # Đánh giá
    train_preds = model_pipeline.predict(X_train)
    test_preds = model_pipeline.predict(X_test)
    accuracy_train = accuracy_score(y_train, train_preds)
    accuracy_test = accuracy_score(y_test, test_preds)
    report = classification_report(y_test, test_preds)

    return model_pipeline, accuracy_train, accuracy_test, report

def predict(pipeline, product_names):
    """
    Dự đoán danh mục và độ chắc chắn cho danh sách sản phẩm.
    :return: list of tuples [('Predicted Category Name', confidence_score), ...]
    """
    if not product_names:
        return []
        
    cleaned_names = [preprocess_text(name) for name in product_names]
    
    predictions = pipeline.predict(cleaned_names)
    probabilities = pipeline.predict_proba(cleaned_names)
    
    results = []
    for i, pred_class in enumerate(predictions):
        # Lấy xác suất cao nhất tương ứng với lớp đã dự đoán
        class_index = list(pipeline.classes_).index(pred_class)
        confidence = probabilities[i][class_index]
        results.append((pred_class, confidence))
        
    return results

