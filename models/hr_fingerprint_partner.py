from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class PartnerFingerprintMachine(models.Model):
    _inherit = 'res.partner'

    _sql_constraints = [
        ('unique_fingerprint_user_number', 'unique(fingerprint_user_number)', 'Fingerprint User Number must be unique!')
    ]

    fingerprint_user_number = fields.Char(string='Fingerprint User Number', help='fingerprint user number is the user_id in fingerprint devices')

    # def unlink(self):
    #     for partner in self:
    #         # Check if this partner is linked to any hr.fingerprint.user record
    #         linked_fingerprint_users = self.env['hr.fingerprint.user'].search([('partner_id', '=', partner.id)])
    #         if linked_fingerprint_users:
    #             raise UserError(_("You cannot delete this partner because they are linked to an active fingerprint user: %s. Please unlink the fingerprint user first.") % (linked_fingerprint_users[0].name))
    #     return super().unlink()
