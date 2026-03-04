# models/survey_question.py
from odoo import models, fields, Command
from odoo.http import request

class SurveyQuestion(models.Model):
    _inherit = 'survey.question'

    images_on_fail_allowed = fields.Boolean(string="Không đạt có thể upload ảnh")


# models/survey_user_input_line.py
class SurveyUserInputLine(models.Model):
    _inherit = 'survey.user_input.line'

    # image_attachment_ids = fields.Many2many('ir.attachment', string="Ảnh minh chứng")
    answer_type = fields.Selection(
        selection_add=[('image_upload', 'Image Upload')],
        ondelete={'image_upload': 'cascade'})
    value_image_upload = fields.Many2many('ir.attachment', string="Ảnh minh chứng")

class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    def _extract_image_from_answers(self, question, answers):
        image = []
        answers_no_image = []
        if answers:
            for answer in answers:
                if isinstance(answer, dict) and 'files' in answer:
                    for file in answer['files']:
                        attachment = request.env['ir.attachment'].sudo().create({
                            'name': f"{question.id}_image_comment",
                            'type': 'binary',
                            'datas': file,
                        })
                        image.append(attachment)
                else:
                    answers_no_image.append(answer)
        return answers_no_image, image

    def _get_line_image_values(self, question, image_attachment_ids):
        return {
            'user_input_id': self.id,
            'question_id': question.id,
            'skipped': False,
            'answer_type': 'image_upload',
            'value_image_upload': image_attachment_ids,
        }

    def _save_line_choice(self, question, old_answers, answers, comment):
        if question.question_type != 'simple_choice' or len(answers) < 1:
            return super()._save_line_choice(question, old_answers, answers, comment)

        if not (isinstance(answers, list)):
            answers = [answers]

        if not answers:
            # add a False answer to force saving a skipped line
            # this will make this question correctly considered as skipped in statistics
            answers = [False]

        vals_list = []
        answer, images = self._extract_image_from_answers(question, answers)

        if not question.comment_count_as_answer or not question.comments_allowed or not comment:
            vals_list = [self._get_line_answer_values(question, ans, 'suggestion') for ans in answer]
        if images:
            image_attachment_ids = [Command.link(image.id) for image in images]
            vals_list.append(self._get_line_image_values(question, image_attachment_ids))
        if comment:
            vals_list.append(self._get_line_comment_values(question, comment))

        old_answers.sudo().unlink()
        return self.env['survey.user_input.line'].create(vals_list)

