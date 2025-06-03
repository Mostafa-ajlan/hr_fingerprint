from odoo import api, fields, models

class PartnerFingerprintMachine(models.Model):
    _inherit = 'res.partner'

    fingerprint_user_number = fields.Char(string='Fingerprint User Number', help='fingerprint user number is the user_id in fingerprint devices')
