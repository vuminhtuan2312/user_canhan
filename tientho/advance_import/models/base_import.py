from odoo import models, fields, api, registry, _
from odoo.modules.registry import Registry
import json
import threading
import time
from odoo.addons.base_import.models.base_import import ImportValidationError

import logging
_logger = logging.getLogger(__name__)

class Import(models.TransientModel):
    _inherit = 'base_import.import'

    row_start = fields.Integer('Import từ dòng')
    row_total = fields.Integer('Tổng số dòng')
    json_fields = fields.Char('Fields')
    json_options = fields.Char('Options')
    is_schedule = fields.Boolean('Schedule import', default=False)

    def execute_import(self, fields, columns, options, dryrun=False):

        advance_options = {
            'in_background': options.get('in_background'),
            'create_only': options.get('create_only'),
            'update_only': options.get('update_only'),
            'skip_row_error': options.get('skip_row_error'),
            'commit_per_record': options.get('commit_per_record'),
        }
        file_name = self.file_name

        is_adavance = any(advance_options.values())

        if advance_options.get('create_only') or options.get('check_for_duplicates'):
            self.check_condition_import(fields, options)
        if options.get('linking'):
            ctx = self.env.context.copy()
            ctx.update({'linking': options.get('linking')})
            self.env.context = ctx
        if not is_adavance or dryrun:
            return super().execute_import(fields, columns, options, dryrun)
        # Cmt do hàm execute_import_advance chỉ nhận 2 giá trị thay vì 4
        # if not advance_options['in_background']:
        #     result = self.execute_import_advance(fields, columns, options, dryrun)
        # else:
        origin = {
            'rec_id': self.id,
            'user_id': self.env.user.id,
            'context': self._context,
            'dbname': self._cr.dbname,
        }

        self.write({
            'json_fields': json.dumps(fields),
            'json_options': json.dumps(options),
            'is_schedule': True,
        })
        self.flush_model()
        threaded_do_schedule = threading.Thread(target=self._threading_do_schedule, args=(origin, columns))
        threaded_do_schedule.start()

        result = {'schedule_completed': True, 'file_name': file_name, 'ids': [-1]}

        return result

    def _threading_do_schedule(self, origin, columns=False):
        _logger.info("Chờ 5 giây để lệnh khác commit...")
        time.sleep(5)
        with Registry(origin['dbname']).cursor() as cr:
            env = api.Environment(cr, origin['user_id'], origin['context'])
            record = env[self._name].browse(origin['rec_id'])
            record.execute_import_advance(columns)
            cr.commit()


    def execute_import_advance(self, columns=False, row_start=False):
        self.ensure_one()

        fields = json.loads(self.json_fields or '{}')
        options = json.loads(self.json_options or '{}')
        file_info = f'{self.create_uid.id}-{self.id}-{self.file_name}'
        row_start = row_start or self.row_start

        _logger.info('File: %s bắt đầu chạy chế độ advance import' % file_info)

        advance_options = {
            'in_background': options.get('in_background'),
            'create_only': options.get('create_only'),
            'update_only': options.get('update_only'),
            'skip_row_error': options.get('skip_row_error'),
            'commit_per_record': options.get('commit_per_record'),
        }

        try:
            input_file_data, import_fields = self._convert_import_data(fields, options)
            # Parse date and float field
            input_file_data = self._parse_import_data(input_file_data, import_fields, options)
        except ImportValidationError as error:
            _logger.info('%s Không import được do lỗi %s', file_info, str(error.__dict__))
            return {'messages': [error.__dict__]}

        _logger.info('%s, importing %d rows...', file_info, len(input_file_data))
        self.row_total = len(input_file_data)

        binary_filenames = self._extract_binary_filenames(import_fields, input_file_data)

        import_fields, merged_data = self._handle_multi_mapping(import_fields, input_file_data)

        if options.get('fallback_values'):
            merged_data = self._handle_fallback_values(import_fields, merged_data, options['fallback_values'])
        
        name_create_enabled_fields = options.pop('name_create_enabled_fields', {})
        import_limit = options.pop('limit', None)
        model = self.env[self.res_model].with_context(
            import_file=True,
            name_create_enabled_fields=name_create_enabled_fields,
            import_set_empty_fields=options.get('import_set_empty_fields', []),
            import_skip_records=options.get('import_skip_records', []),
            _import_limit=import_limit)
        
        # import_result = model.load(import_fields, merged_data)
        import_result = {'ids': []}
        index = 0
        for m_data in merged_data:
            index += 1
            if row_start and index < row_start: continue
            _logger.info('%s importing row %d', file_info, index)
            try:
                i_result = model.load(import_fields, [m_data])

                if i_result.get('ids'):
                    import_result['ids'] += i_result.get('ids')
                    _logger.info('%s, import thành công dòng %d', file_info, index)
                else:
                    _logger.info('%s, import thất bại dòng %d, lỗi: %s', file_info, index, str(i_result))
                    if not advance_options['skip_row_error']:
                        _logger.info('%s, Dừng do có dòng bị lỗi', file_info)
                        break

                self.row_start = index
                if advance_options['commit_per_record']:
                    self.env.cr.commit()
            except Exception as e:
                if advance_options['commit_per_record']:
                    self.env.cr.rollback()
                _logger.info('%s, Lỗi exception khi import %s', file_info, str(e))
                pass
        
        _logger.info('%s, done', file_info)

        # Insert/Update mapping columns when import complete successfully
        if columns and import_result['ids'] and options.get('has_headers'):
            BaseImportMapping = self.env['base_import.mapping']
            for index, column_name in enumerate(columns):
                if column_name:
                    # Update to latest selected field
                    mapping_domain = [('res_model', '=', self.res_model), ('column_name', '=', column_name)]
                    column_mapping = BaseImportMapping.search(mapping_domain, limit=1)
                    if column_mapping:
                        if column_mapping.field_name != fields[index]:
                            column_mapping.field_name = fields[index]
                    else:
                        BaseImportMapping.create({
                            'res_model': self.res_model,
                            'column_name': column_name,
                            'field_name': fields[index]
                        })
            _logger.info('%s updated column mapping', file_info)

        return import_result

    def check_condition_import(self, fields, options):
        input_file_data, import_fields = self._convert_import_data(fields, options)
        input_file_data = self._parse_import_data(input_file_data, import_fields, options)
        check_duplicate = options.get('check_for_duplicates')
        # Các trường cần kiểm tra trùng nhưng chỉ lấy các trường nằm trong import_fields hoặc có trong check_for_duplicates
        if check_duplicate:
            duplicate_fields = [f for f in check_duplicate if f in import_fields]
        else:
            duplicate_fields = import_fields
        model = self.env[self.res_model]

        duplicate_errors = []

        # Bỏ qua header nếu file có headers
        start_index = 0

        for row_index, row in enumerate(input_file_data[start_index:], start=start_index + 1):
            row_data = dict(zip(import_fields, row))

            for field in duplicate_fields:
                value = row_data.get(field)
                if not value:
                    continue  # không có giá trị thì bỏ qua

                # Kiểm tra trong database xem có trùng không
                domain = [(field, '=', value)]
                existed = model.search(domain, limit=1)

                if existed:
                    duplicate_errors.append({
                        'row': row_index,
                        'field': field,
                        'value': value,
                        'existing_id': existed.id,
                    })

        # Nếu có lỗi trùng → xử lý
        if duplicate_errors:
            messages = []
            for err in duplicate_errors:
                messages.append(
                    f"Row {err['row']}: Field '{err['field']}' "
                    f"with value '{err['value']}' already exists (record ID {err['existing_id']})."
                )
            raise ImportValidationError("Duplicate data found:\n" + "\n".join(messages))

