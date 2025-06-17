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

    # Update the fingerprint user number associations between partners and fingerprint users
    def _update_fingerprint_user_number(self):
        for partner in self:
            # Unlink any existing fingerprint user records associated with this partner
            fingerprint_users = self.env['hr.fingerprint.user'].sudo().search([
                ('partner_id', '=', partner.id)
            ])
            if fingerprint_users:
                self.env.cr.execute(
                    "UPDATE hr_fingerprint_user SET partner_id = NULL WHERE partner_id = %s",
                    (partner.id,)
                )
            # Link the fingerprint user record with the new fingerprint_user_number to this partner
            if partner.fingerprint_user_number:
                fingerprint_users = self.env['hr.fingerprint.user'].sudo().search([
                    ('user_id', '=', partner.fingerprint_user_number)
                ])
                if fingerprint_users:
                    self.env.cr.execute(
                        "UPDATE hr_fingerprint_user SET partner_id = %s WHERE user_id = %s",
                        (partner.id, partner.fingerprint_user_number)
                    )
                    
    @api.model
    def create(self, vals):
        partners = super(PartnerFingerprintMachine, self).create(vals)
        if vals.get('fingerprint_user_number'):
            self._update_fingerprint_user_number()
        return partners
    
    def write(self, vals):
        # Only override write for this inherited model, not the base class
        res = super(PartnerFingerprintMachine, self).write(vals)
        if 'fingerprint_user_number' in vals:
            self._update_fingerprint_user_number()
        return res


