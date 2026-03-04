from odoo import models, fields, tools
from odoo.tools import SQL

class ProjectTaskActivity1(models.Model):
    _name = 'project.task.activity'    
    _inherits = {'project.task': 'task_id'}
    _auto = False
    _order = 'activity_date desc'

    task_id = fields.Many2one('project.task')
    activity_type = fields.Selection([('activity', 'Activity'), ('github', 'PR github'), ('state', 'Change state'), ('assigned', 'Assign task')])
    activity_id = fields.Many2one('mail.message')
    subtype_id = fields.Many2one('mail.message.subtype')
    activity_user_id = fields.Many2one('res.users')
    activity_date = fields.Datetime()

    body = fields.Text()

    @property
    def _table_query(self):
        return """
            select
                row_number() over (order by task_id, activity_type, activity_id) as id,
                *
            from (
                -- activity
                select 
                    'activity' as activity_type,
                    res_id as task_id, 
                    id as activity_id,
                    subtype_id,
                    create_uid as activity_user_id, 
                    create_date as activity_date,

                    body
                from 
                    mail_message 
                where model = 'project.task' and message_type != 'user_notification'
                
                -- github
                union all
                select
                    'github' as activity_type,
                    res_id task_id,
                    id as activity_id, 
                    subtype_id,
                    create_uid as activity_user_id, 
                    create_date as activity_date,

                    (regexp_match(body, '(https?://github\\.com/[^\\s"''<>]+)'))[1] as body
                from 
                    mail_message 
                where 
                    model = 'project.task' and message_type != 'user_notification'
                    and body ilike '%%github.com%%'
                
                -- state change
                union all
                select
                    'state' as activity_type,
                    mm.res_id as task_id,
                    mm.id as activity_id,
                    mm.subtype_id,
                    mm.create_uid as activity_user_id, 
                    mm.create_date as activity_date,

                    concat(mtv.old_value_char, ' -> ', mtv.new_value_char) as body
                from
                    mail_message mm
                    join mail_tracking_value mtv on mtv.mail_message_id = mm.id and model = 'project.task' and message_type != 'user_notification'
                    join ir_model_fields imf on imf.id = mtv.field_id and imf.name = 'stage_id'

                -- assigned
                union all
                SELECT
                    'assigned' as activity_type,
                    mm.res_id AS task_id,
                    mm.id as activity_id,
                    mm.subtype_id,
                    NULL as activity_user_id,
                    mm.create_date AS activity_date,

                    TRIM(added_user_raw) AS body
                FROM mail_message mm
                JOIN mail_tracking_value mtv ON mtv.mail_message_id = mm.id
                JOIN ir_model_fields imf ON imf.id = mtv.field_id
                -- Tách từng user trong new_value_char
                JOIN LATERAL regexp_split_to_table(mtv.new_value_char, E'\\s*,\\s*') AS added_user_raw ON TRUE
                WHERE mm.model = 'project.task'
                  AND mm.message_type != 'user_notification'
                  AND imf.name = 'user_ids'
                  AND mtv.new_value_char IS NOT NULL
                  AND mtv.old_value_char IS NOT NULL
                  -- Điều kiện lọc: chỉ lấy user chưa có trong old_value_char
                  AND POSITION(added_user_raw IN mtv.old_value_char) = 0
            ) as combined
        """
