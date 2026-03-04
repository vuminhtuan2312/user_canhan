from odoo.exceptions import UserError
from odoo import api, fields, models
list_criteria = ['Trình độ học vấn', 'Kinh nghiệm cho vị trí công việc', 'Kinh nghiệm theo công việc', 'Kiến thức',
                 'Kỹ năng chuyên môn', 'Kỹ năng mềm', 'Phù hợp phẩm chất cốt lõi', 'Tác phong']

class ReportTemplateEvaluationForm(models.AbstractModel):
    _name = 'report.ttb_hr.template_evaluation_form_document'
    _description = 'Báo cáo phiếu đánh giá ứng viên'

    @api.model
    def _get_report_values(self, docids, data=None):
        # Lấy dữ liệu từ hr.applicant (theo action đã cấu hình)
        docs = self.env['hr.applicant'].browse(docids)

        processed_data = []
        for doc in docs:
            lines = doc.gen_content_value(doc.job_id)
            data_row = {
                'id': doc.id,  # Giữ ID gốc từ hr.applicant
                'name': doc.candidate_id.display_name if doc.candidate_id else '',
                'job_name': doc.job_id.name if doc.job_id else '',
                'department_name': doc.job_id.department_id.name if doc.job_id and doc.job_id.department_id else '',
                'lines': lines,
                'list_criteria': list_criteria,
            }
            processed_data.append(data_row)

        return {
            'doc_ids': docids,
            'doc_model': 'hr.applicant',
            'docs': processed_data,  # Trả về original Odoo records
            'company': self.env.company,
            'o': docs[0] if docs else None,  # Truy cập đối tượng hr.applicant đầu tiên
        }

