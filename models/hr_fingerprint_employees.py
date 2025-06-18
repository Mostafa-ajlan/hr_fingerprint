from odoo import _, api, fields, models , _
from odoo.exceptions import ValidationError


class Employee(models.Model):
    _inherit = 'hr.employee'

    fingerprint_user_number = fields.Char(related='work_contact_id.fingerprint_user_number', readonly=False, string=_('Fingerprint User Number'), help=_('fingerprint user number is the user_id in fingerprint devices'))