from odoo import models, fields, api

class SgkBookImages(models.Model):
    _name = 'sgk.book.images'
    _description = 'Ảnh barcode gom theo tên sách'

    name_sgk = fields.Char(string='Tên sách')
    image_ids = fields.Many2many('ir.attachment', string='Ảnh barcode')
    barcode_ids = fields.Text(string='Mã barcode')

    def _normalize_barcodes(self, text):
        if not text:
            return ''
        parts = text.replace('\n', ' ').replace('\t', ' ').split()
        return ','.join(parts)

    @api.model
    def create(self, vals):
        if 'barcode_ids' in vals:
            vals['barcode_ids'] = self._normalize_barcodes(vals['barcode_ids'])
        return super().create(vals)

    def write(self, vals):
        if 'barcode_ids' in vals:
            vals['barcode_ids'] = self._normalize_barcodes(vals['barcode_ids'])
        return super().write(vals)

    @api.model
    def generate_records(self):
        books = self.env['sgk.book'].search([])
        name_group = {}

        for book in books:
            if book.name_sgk:
                name_group.setdefault(book.name_sgk, []).extend(book.image_ids.ids)

        for name_sgk, image_ids in name_group.items():
            existing = self.search([('name_sgk', '=', name_sgk)], limit=1)
            if existing:
                new_image_ids = list(set(image_ids) - set(existing.image_ids.ids))
                if new_image_ids:
                    existing.write({
                        'image_ids': [(4, img_id) for img_id in new_image_ids]
                    })
            else:
                self.create({
                    'name_sgk': name_sgk,
                    'image_ids': [(6, 0, list(set(image_ids)))],
                })
