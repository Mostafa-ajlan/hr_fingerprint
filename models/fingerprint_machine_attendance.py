from odoo import api, fields, models , _


class FingerprintMachineAttendance(models.Model):
    """Model to hold data from the Fingerprint device"""
    _name = 'fingerprint.attendance'
    _description = _('Attendance')
    _order = 'punching_time desc'
    # rec_name = 'user_id.name'
    
    device_id = fields.Many2one(
        'hr.fingerprint.device',
        string=_('Fingerprint Device'),
        readonly=True,
        required=True
    )
    user_id = fields.Many2one(
        'hr.fingerprint.user',
        string=_('User')
    )
    partner_id = fields.Many2one(
        related='user_id.partner_id',
        string="Partner",
        store=True,
        readonly=True
    )
    is_used = fields.Boolean(string=_('Is Used'), default=False)
    punch_type = fields.Selection([
            ('0', _("Check In")),
            ('1', _("Check Out")),
            ('2', _("Break Out")),
            ('3', _("Break In")),
            ('4', _("Overtime In")),
            ('5', _("Overtime Out")),
        ],
        string=_('Punching Type'),
        help=_('Punching type of the attendance')
    )
    attendance_type = fields.Selection([
            ('1', _("Finger")), 
            ('15', _("Face")),
            ('2', _("Type_2")),
            ('25', _("Palm")), 
            ('3', _("Password")),
            ('4', _("Card")),
            ('255', _("Duplicate"))
        ],
        string=_('Category'),
        help=_("Attendance detecting methods")
    )

    punching_time = fields.Datetime(
        string=_('Punching Time'),
        help=_("Punching time in the device")
    )
    

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'user_id' in vals:
                user = self.env['hr.fingerprint.user'].browse(vals['user_id'])
                vals['user_id'] = user.id if user.exists() else False

        return super().create(vals_list)        