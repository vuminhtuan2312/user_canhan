from odoo import api, fields, models, _

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'


    def message_post(self, **kwargs):
        """
        Khi user comment trên Ticket:
        - Gửi notify cho: Người xử lý (user_id), GĐ cơ sở, QL cơ sở,
          và tất cả người được @mention trong comment.
        - Chặn vòng lặp bằng context 'ttb_skip_comment_notify'.
        """
        # Bỏ qua nếu chính notify của mình sẽ gọi lại (tránh vòng lặp)
        if self.env.context.get('ttb_skip_comment_notify'):
            return super().message_post(**kwargs)

        # Đăng comment như bình thường trước
        msg = super().message_post(**kwargs)

        # Chỉ xử lý với comment "thật" của người dùng
        subtype = kwargs.get('subtype_xmlid')
        mtype   = kwargs.get('message_type')
        is_comment = (mtype == 'comment') or (mtype in (None, '') and (subtype in (None, 'mail.mt_comment')))

        if not is_comment:
            return msg

        author_user = self.env.user

        # Với mỗi ticket trong self (thực tế thường là 1)
        for ticket in self:
            users = self.env['res.users'].sudo().browse()

            # 1) Người xử lý
            if ticket.user_id:
                users |= ticket.user_id

            # 2) GĐ/QL cơ sở
            if getattr(ticket.ttb_branch_id, 'director_id', False):
                users |= ticket.ttb_branch_id.director_id
            if getattr(ticket.ttb_branch_id, 'manager_id', False):
                users |= ticket.ttb_branch_id.manager_id

            # 3) Tất cả người được tag trong comment (partner_ids của message)
            mentioned_partners = msg.partner_ids
            mentioned_users = mentioned_partners.mapped('user_ids')
            users |= mentioned_users

            # Không gửi cho chính người bình luận
            users -= author_user

            if users:
                message = _("%(who)s đã bình luận về ticket của bạn") % {'who': author_user.name}
                # Truyền context để khi send_notify() gọi message_post() nội bộ thì không kích hoạt lại hàm này
                ticket.with_context(ttb_skip_comment_notify=True).send_notify(message, users)

        return msg
