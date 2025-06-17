from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class PartnerFingerprintMachine(models.Model):
    _inherit = 'res.partner'

    _sql_constraints = [
        ('unique_fingerprint_user_number', 'unique(fingerprint_user_number)', _('Fingerprint User Number must be unique!'))
    ]

    fingerprint_user_number = fields.Char(
        string=_("Fingerprint User Number"),
        help=_("fingerprint user number is the user_id in fingerprint devices")
    )

    def write(self, vals):
        res = super().write(vals)
        if 'fingerprint_user_number' in vals:
            for partner in self:
                # البحث عن أي مستخدم بصمة مرتبط بهذا الشريك وفك الربط
                fingerprint_users = self.env['hr.fingerprint.user'].sudo().search([
                    ('partner_id', '=', partner.id)
                ])
                if fingerprint_users:
                    fingerprint_users.write({'partner_id': False})
        return res

    def unlink(self):
        for partner in self:
            # Find all hr.fingerprint.user records linked to this partner and unlink them
            fingerprint_users = self.env['hr.fingerprint.user'].sudo().search([('partner_id', '=', partner.id)])
            if fingerprint_users:
                fingerprint_users.write({'partner_id': False})
        return super().unlink()

