import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

try:
    from zk import ZK, const
except ImportError:
    _logger.error("Please install pyzk library: pip install pyzk")

class HrFingerprintUser(models.Model):
    _name = 'hr.fingerprint.user'
    _description = _('Fingerprint User')
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'  # Display name in the UI 
    _order = 'create_date desc, name'  # Order by creation date (desc) and then by name

    _sql_constraints = [
        ('unique_uid_per_device', 'unique(uid, device_id)', 'UID must be unique per device!'),
        ('unique_user_id_per_device', 'unique(user_id, device_id)', 'User ID must be unique per device!'),
    ]  
    name = fields.Char(string=_('Name'), required=True)  

    device_id = fields.Many2one(
        'hr.fingerprint.device', 
        string=_('Device'), 
        required=True, 
        ondelete='cascade',
    ) 
    connection_device_mode = fields.Selection(related='device_id.connection_mode', string=_('Connection Device Mode'), readonly=True)
    
    partner_id = fields.Many2one(
        'res.partner',
        string=_("Partner"),
        domain=lambda self: self._get_available_partners(),
        ondelete='set null'
    )
    user_id = fields.Char(
        string=_("User ID"), 
        default=False,
        readonly=False,
        index=True,
        help=_('User ID in the fingerprint device')
    )
    uid = fields.Char(
        string=_("UID"), 
        default=False,
        help=_('Unique ID for the user in the fingerprint device')
    )
    privilege = fields.Selection([
        ('0', 'User'),
        ('2', 'Enroller'),
        ('6', 'Admin'),
        ('14', 'Super Admin')
    ], string=_('Privilege'), default='0',)

    password = fields.Char(string=_('Password'),)
    group_id = fields.Char(string=_('Group ID'))
    card = fields.Char(string=_('Card Number'),)
    active_user = fields.Boolean(default=True)

    image = fields.Char(string=_('Image'), attachment=True)
    image_filename = fields.Char(string=_('Image File Name'), help=_("File name of the user photo"))
    image_size = fields.Integer(string=_('Image Size (bytes)'), help=_("Size of the user photo in bytes"))
    start_datetime = fields.Datetime(string=_('Start Validity'), help=_("Start date and time for user validity"))
    end_datetime = fields.Datetime(string=_('End Validity'), help=_("End date and time for user validity"))

    template_ids = fields.One2many('hr.fingerprint.template', 'user_id', string=_('Fingerprints'), help=_("Fingerprints associated with this user"))
    biometric_data_ids = fields.One2many(
        'hr.fingerprint.user.biometric', 'user_id', string=_('Biometric Data')
    )
    attendance_ids = fields.One2many(
        'fingerprint.attendance', 
        'user_id', 
        string=_('Attendances')
    )
    

    @api.onchange('user_id')
    def _onchange_user_id_set_partner(self):
        if self.user_id:
            partner = self.env['res.partner'].sudo().search([('fingerprint_user_number', '=', self.user_id)], limit=1)
            self.partner_id = partner.id if partner else False
        else:
            self.partner_id = False
    
    # def _get_available_partners(self):
    #     used_partner_ids = self.env['hr.fingerprint.user'].search([]).mapped('partner_id.id')
    #     domain = [
    #         ('id', 'not in', used_partner_ids),
    #         ('fingerprint_user_number', '!=', False)
    #     ]
    #     return domain
    
    def _get_available_partners(self):
        # Allow current partner when editing
        other_users = self.env['hr.fingerprint.user'].search([('id', '!=', self._origin.id)])
        used_partner_ids = other_users.mapped('partner_id.id')
        domain = [
            ('id', 'not in', used_partner_ids),
            ('fingerprint_user_number', '!=', False)
        ]
        return domain
    
    
    def _sync_user_in_device(self, device, user=None, vals=None):
        '''
        تضيف أو تحدث مستخدم في جهاز البصمة.
        إذا كان user=None سيتم استخدام القيم من vals فقط (إنشاء).
        إذا كان user موجود سيتم استخدام القيم من vals وإذا لم توجد يرجع لقيم user (تحديث).
        '''
        try:
            zk_device, conn = device.connect_to_zk_device()
            if not zk_device or not conn:
                _logger.error("Could not connect to device %s", device.name)
                return False
            try:
                # تجهيز البيانات
                uid_to_send = int(user.uid) if user and user.uid else None
                user_id = vals.get('user_id') if vals and 'user_id' in vals else (user.user_id if user else '')
                name = vals.get('name') if vals and 'name' in vals else (user.name if user else '')
                password = vals.get('password') if vals and 'password' in vals else (user.password if user else '')
                group_id = vals.get('group_id') if vals and 'group_id' in vals else (user.group_id if user else '')
                _privilege_from_vals = vals.get('privilege') if vals and 'privilege' in vals else None
                privilege = int(_privilege_from_vals) if _privilege_from_vals is not None else (int(user.privilege) if user and user.privilege is not None else 0)
                _card_from_vals = vals.get('card') if vals and 'card' in vals else None
                card = int(_card_from_vals) if _card_from_vals is not None else (int(user.card) if user and user.card is not None else 0)               
                conn.set_user(
                    uid=uid_to_send,
                    name=name,
                    privilege=privilege,
                    password=password if password else '',
                    group_id=group_id if group_id else '',
                    user_id=user_id,
                    card=int(card) if card and str(card).isdigit() else 0
                )
                _logger.info("User %s synced successfully in device %s", name, device.name)
                return True
            except Exception as e:
                _logger.error("Error syncing user in device %s: %s", device.name, str(e))
                return False
            finally:
                if conn:
                    conn.disconnect()
        except Exception as e:
            _logger.error("Error connecting to device %s: %s", device.name, str(e))
            return False
        
    @api.model_create_multi
    def create(self, vals_list):
        
        result_records = self.env['hr.fingerprint.user']
        for vals in vals_list:
            # Auto-link partner if user_id is provided and partner_id is not
            if not vals.get('partner_id') and vals.get('user_id'):
                partner = self.env['res.partner'].sudo().search([('fingerprint_user_number', '=', vals.get('user_id'))], limit=1)
                if partner:
                    vals['partner_id'] = partner.id
                    
            # إذا لم يكن الطلب من الواجهة الأمامية، فقط احفظ في القاعدة
            if not self.env.context.get('from_frontend'):
                record = super(HrFingerprintUser, self).create([vals])
                result_records += record
                continue

            mode = vals.get('connection_device_mode') or self.env['hr.fingerprint.device'].browse(vals.get('device_id')).connection_mode
            if mode == 'direct':
                device = self.env['hr.fingerprint.device'].browse(vals['device_id'])
                if not self._sync_user_in_device(device, user=None, vals=vals):
                    raise UserError(_("Failed to add the user to the device. The user was not saved because the device is unavailable."))
                user_in_device = device._fetch_user_by_user_id(vals.get('user_id',''))
                if not user_in_device:
                    raise UserError(_("Failed to add the user to the device. The user was not saved because the device is unavailable."))
                vals['uid'] = user_in_device.get('uid', False)
                record = super(HrFingerprintUser, self).create([vals])
                result_records += record
            elif mode == 'push':
                # pass
                try:
                    dict_vals={}
                    device = self.env['hr.fingerprint.device'].browse(vals['device_id'])
                    if not device:
                        raise UserError(_("Device not found."))
                    dict_vals['name'] = 'update user'
                    dict_vals['command_type'] = 'update_userinfo'
                    dict_vals['user_id'] = vals.get('user_id')
                    dict_vals['device_id'] = device.id 
                    dict_vals['name_value'] = vals.get('name') or None
                    dict_vals['password'] = vals.get('password') or None
                    dict_vals['card'] = vals.get('card') or None
                    dict_vals['group_id'] = vals.get('group_id') or None
                    dict_vals['privilege'] = vals.get('privilege') or None
                    device = self.env['zk.device.command'].create(dict_vals)
                except Exception as e:
                    print(e)
                # if not self._sync_user_in_device(user.device_id, user=user, vals=vals):
                    raise UserError(_("فشل تحديث المستخدم في جهاز البصمة (push). لم يتم حفظ التعديلات."))
                # if not self._sync_user_in_device(device, user=None, vals=vals):
                #     raise UserError(_("فشل إضافة المستخدم للجهاز (push). لم يتم حفظ المستخدم."))
                record = super(HrFingerprintUser, self).create([vals])
                result_records += record
            elif mode == 'iot':
                if not self.env.context.get('iot_synced'):
                    raise UserError(_("You must sync the user with the IoT device first before saving."))
                record = super(HrFingerprintUser, self).create([vals])
                result_records += record
            else:
                record = super(HrFingerprintUser, self).create([vals])
                result_records += record
        return result_records

    def write(self, vals):
        for user in self:
            # منع تعديل الجهاز أو user_id بعد الإنشاء
            # if 'device_id' in vals and vals['device_id'] != user.device_id.id:
            #     raise UserError(_("Device cannot be modified after user creation."))
            # if 'user_id' in vals and vals['user_id'] != user.user_id:
            #     raise UserError(_("User ID cannot be modified after creation."))

            # إذا كان هناك تغيير في user_id، قم بتحديث partner_id
            # if vals.get('partner_id'):
            #     if vals.get('partner_id') is not False:
            #         partner = self.env["res.partner"].sudo().search(
            #             [('id', '=', vals.get('partner_id'))], limit=1
            #         )
            #         # Check if the partner already has a fingerprint_user_number
            #         # and it is different from the current user_id
            #         if partner.fingerprint_user_number and partner.fingerprint_user_number != user.user_id:
            #             raise UserError(_("This partner is already linked to another fingerprint user number (%s). "
            #                     "It cannot be linked to a different number."
            #                 )
            #                 % partner.fingerprint_user_number
            #             )
            #         user_id_users = self.env['hr.fingerprint.user'].sudo().search(
            #             [('user_id', '=', user.user_id),('id', '!=', user.id),('partner_id', '!=', False)]
            #         )
            #         if user_id_users:
            #             # إذا كان هناك مستخدمين آخرين بنفس user_id مرتبطين بجهة اتصال مختلفة، ارفع خطأ
            #             # هذا يمنع ربط نفس user_id بجهات اتصال مختلفة
            #             for u in user_id_users:
            #                 if u.partner_id.id != partner.id:
            #                     raise UserError(_("This user ID is already linked to another partner (%s). "
            #                             "It cannot be linked to a different partner."
            #                         )
            #                         % u.partner_id.name
            #                     )
            #         try:
            #             partner.fingerprint_user_number = user.user_id
            #         except Exception as e:
            #             old_fingerprint_user_number = None
            #             partner.fingerprint_user_number = old_fingerprint_user_number
            #             raise UserError(
            #                 _(
            #                     "An error occurred while updating the fingerprint user number "
            #                     "for the partner: %s"
            #                 )
            #                 % str(e)
            #             )
            
            # elif vals.get('partner_id') == False:
            #     # إذا تم إفراغ جهة الاتصال، أفرغ رقم المستخدم في جهة الاتصال إذا لم يوجد مستخدمين آخرين بنفس الرقم
            #     other_users = self.env['hr.fingerprint.user'].sudo().search([
            #         ('partner_id', '=', user.partner_id.id),
            #         ('id', '!=', user.id),
            #         ('user_id', '=', user.user_id)
            #     ], limit=1)
            #     if not other_users:
            #         partner = self.env["res.partner"].sudo().search([('id', '=', user.partner_id.id)], limit=1)
            #         self.env.cr.execute(
            #             "UPDATE res_partner SET fingerprint_user_number = NULL WHERE id = %s",
            #             (partner.id,)
            #         )
                    

            # إذا لم يكن الطلب من الواجهة الأمامية، فقط عدل في القاعدة
            if not self.env.context.get('from_frontend'):
                return super(HrFingerprintUser, user).write(vals)

            mode = user.connection_device_mode
            if mode == 'direct':
                if not self._sync_user_in_device(user.device_id, user=user, vals=vals):
                    raise UserError(_("Failed to update the user in the fingerprint device. Changes were not saved."))
                return super(HrFingerprintUser, user).write(vals)
            elif mode == 'push':
                try:
                    dict_vals={}

                    dict_vals['name'] = 'update user'
                    dict_vals['command_type'] = 'update_userinfo'
                    dict_vals['user_id'] = user.user_id
                    dict_vals['device_id'] = user.device_id.id
                    dict_vals['name_value'] = vals.get('name') or None
                    dict_vals['password'] = vals.get('password') or None
                    dict_vals['card'] = vals.get('card') or None
                    dict_vals['group_id'] = vals.get('group_id') or None
                    dict_vals['privilege'] = vals.get('privilege') or None
                    device = self.env['zk.device.command'].create(dict_vals)
                except Exception as e:
                    print(e)
                # if not self._sync_user_in_device(user.device_id, user=user, vals=vals):
                    raise UserError(_("فشل تحديث المستخدم في جهاز البصمة (push). لم يتم حفظ التعديلات."))
                return super(HrFingerprintUser, user).write(vals)
            elif mode == 'iot':
                if not self.env.context.get('iot_synced'):
                    raise UserError(_("You must sync the user with the IoT device first before editing."))
                return super(HrFingerprintUser, user).write(vals)
            else:
                return super(HrFingerprintUser, user).write(vals)
            
    def _cleanup_user_relations(self, user):
        """يفصل الحضور والشريك المرتبطين بالمستخدم."""
        attendance_records = self.env['fingerprint.attendance'].search([('user_id', '=', user.id)])
        if attendance_records:
            attendance_records.write({'user_id': False})
        if user.partner_id:
            user.partner_id.fingerprint_user_number = False

    def _delete_user_from_device(self, device, user):
        zk_device, conn = device.connect_to_zk_device()
        print(zk_device,"zk_devicezk_devicezk_device")
        if not zk_device or not conn:
            return False
        try:
            uid = int(user.uid) if user.uid else 0
           
            conn.delete_user(uid=uid, user_id=user.user_id) # استخدام user_id لحذف المستخدم من الجهاز
            conn.disconnect()
            print("TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT")
            return True
        except Exception as e:
            print(e,"FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF")
            return False
        finally:
            if conn:
                conn.disconnect()

    def unlink(self):
        print(self.env.context,"contextcontextcontextcontextcontext")
        users_to_unlink = self.env['hr.fingerprint.user']
        failed_users = []

        for user in self:
            print(user, "selfselfselfselfselfselfselfselfselfself")
            mode = user.connection_device_mode
            if self.env.context.get('from_frontend'):
                if mode == 'direct':
                    if not self._delete_user_from_device(user.device_id, user):
                        failed_users.append(user.name or user.id)
                        continue
                elif mode == 'iot' and not self.env.context.get('iot_synced'):
                    failed_users.append(user.name or user.id)
                    continue
                    
            users_to_unlink += user

        if failed_users:
            raise UserError(_("فشل حذف المستخدمين التاليين من الجهاز: %s") % ', '.join(failed_users))

        # فصل الحضور والشريك ثم الحذف الفعلي
        for user in users_to_unlink:
            self._cleanup_user_relations(user)

        return super(HrFingerprintUser, users_to_unlink).unlink()
        
# Model to hold biometric data for users 
class HRFingerprintUserBiometric(models.Model):
    _name = 'hr.fingerprint.user.biometric'
    _description = _('Biometric Data')

    user_id = fields.Many2one('hr.fingerprint.user', 'User', required=True)
    index = fields.Integer(string=_('Index'))
    valid = fields.Boolean(string=_('Valid'))
    duress = fields.Boolean(string=_('Duress'))
    version_major = fields.Integer(string=_("Major Ver"))
    version_minor = fields.Integer(string=_("Minor Ver"))
    no = fields.Integer()
    type = fields.Integer(string=_('Biometric Type'))  # 2: Palm, 8: Face
    major_ver = fields.Integer()
    minor_ver = fields.Integer()
    format = fields.Integer()
    template = fields.Text(string=_('Biometric Template'))
