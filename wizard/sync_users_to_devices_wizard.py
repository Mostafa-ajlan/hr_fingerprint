from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import requests
import json
import uuid

_logger = logging.getLogger(__name__)


class SyncUsersToDevicesWizard(models.TransientModel):
    _name = 'sync.users.to.devices.wizard'
    _description = 'Sync Users to Devices Wizard'

    device_ids = fields.Many2many('hr.fingerprint.device', string="Devices", required=True)
    user_ids = fields.Many2many('hr.fingerprint.user', string="Users")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        user_ids = self.env.context.get('default_user_ids') or self.env.context.get('active_ids')
        if user_ids:
            res['user_ids'] = [(6, 0, user_ids)]
        return res

    def _prepare_user_values(self, user, device_id):
        return {
            'device_id': device_id,
            'user_id': user.user_id,
            'name': user.name,
            'privilege': user.privilege,
            'password': user.password,
            'group_id': user.group_id,
            'card': user.card,
        }

    def _get_users_to_add(self, device, users):
        existing_user_ids = self.env['hr.fingerprint.user'].search([
            ('device_id', '=', device.id),
            ('user_id', 'in', users.mapped('user_id'))
        ]).mapped('user_id')
        return users.filtered(lambda u: u.user_id not in existing_user_ids)

    def _handle_direct_sync(self, device, users_to_add, results):
        for user in users_to_add:
            vals = self._prepare_user_values(user, device.id)
            try:
                self.env['hr.fingerprint.user'].with_context(from_frontend=True).create(vals)
                results.append(_("تمت إضافة المستخدم %s للجهاز %s (direct)") % (user.name, device.name))
            except Exception as e:
                _logger.exception("Direct sync failed")
                results.append(_("فشل إضافة المستخدم %s للجهاز %s: %s") % (user.name, device.name, str(e)))

    def _handle_iot_sync(self, device, users_to_add, results):
        iot_device = device.iot_device_id
        ip_url = iot_device.iot_id.ip_url if iot_device and iot_device.iot_id else None

        if not ip_url:
            results.append(_("لا يوجد ip_url لجهاز IoT المرتبط بالجهاز %s") % device.name)
            return

        if not self._ping_iot_device(ip_url, iot_device.identifier):
            results.append(_("جهاز IoT لم يستجب أو غير متصل: %s") % device.name)
            return
        
        saved_users = []
        for user in users_to_add:
            vals = self._prepare_user_values(user, device.id)
            try:
                record = self.env['hr.fingerprint.user'].create(vals)
                saved_users.append(record)
                self.env.cr.commit()
                results.append(_("تمت إضافة المستخدم %s للجهاز %s (iot)") % (user.name, device.name))
            except Exception as e:
                _logger.exception("IoT user save failed")
                results.append(_("فشل إضافة المستخدم %s للجهاز %s (iot): %s") % (user.name, device.name, str(e)))

        print(saved_users,"saved_userssaved_userssaved_users")
        if saved_users:
            users_data = [self._prepare_iot_user_data(u) for u in saved_users]
            print(users_data,"users_datausers_datausers_data")
            action_data = {"users": users_data}
            result = self._send_iot_action(ip_url, iot_device, action_data)
            if not result:
                _logger.warning("Saved users but failed to sync to IoT: %s", device.name)
                results.append(_("تم حفظ المستخدمين لكن فشل إرسالهم دفعة واحدة إلى جهاز IoT: %s") % device.name)

    def _prepare_iot_user_data(self, user):
        return {
            "user_id": user.user_id,
            "name": user.name,
            "password": user.password or '',
            "group_id": user.group_id or '',
            "privilege": int(user.privilege) if user.privilege is not None else 0,
            "card": int(user.card) if user.card and str(user.card).isdigit() else 0,
        }

    def _ping_iot_device(self, ip_url, identifier):
        try:
            response = requests.post(
                f"{ip_url}/hw_drivers/ping",
                json={'params': {'device_identifier': identifier}},
                timeout=3,
                headers={'Content-Type': 'application/json;charset=utf-8'}
            )
            return response.ok and response.json().get('result', False) 
        except Exception as e:
            _logger.error("Ping to IoT device failed: %s", e)
            return False

    def _send_iot_action(self, ip_url, iot_device, action_data, action="create_or_update_users"):
        session_id = str(uuid.uuid4())
        params_action = {
            "session_id": session_id,
            "device_identifier": iot_device.identifier,
            "data": json.dumps({
                "action": action,
                "params":{
                    "identifier": iot_device.identifier,
                    **action_data
                }
            }),
        }
        try:
            response = requests.post(
                f"{ip_url}/hw_drivers/action",
                json={"params": params_action},
                timeout=5,
                headers={'Content-Type': 'application/json;charset=utf-8'}
            )
            print(response,"AAAAAAAAAAAAAAAAAAAAAAA")
            print(response.json(),"AAAAAAAAAAAAAAAAAAAAAAA")
            return response.ok and response.json()
        except Exception as e:
            _logger.exception("IoT action request failed")
            return False

    def _handle_push_sync(self, device, users_to_add, results):
        for user in users_to_add:
            vals = self._prepare_user_values(user, device.id)
            try:
                vals['command_type'] = 'update_userinfo'
                vals['state'] = 'pending'
                vals['name_value'] = vals['name'] 
                vals['name'] = 'add user'
                vals['create_uid'] = self.env.user.id
                self.env['zk.device.command'].create(vals)
                self.env.cr.commit()
                results.append(_("تمت جدولة إضافة المستخدم %s للجهاز %s (push)") % (user.name, device.name))
            except Exception as e:
                _logger.exception("Push sync failed")
                results.append(_("فشل جدولة إضافة المستخدم %s للجهاز %s: %s") % (user.name, device.name, str(e)))

    def action_sync(self):
        if not self.device_ids or not self.user_ids:
            raise UserError(_("يجب اختيار مستخدمين وأجهزة!"))

        results = []
        for device in self.device_ids:
            users_to_add = self._get_users_to_add(device, self.user_ids)

            if not users_to_add:
                results.append(_("كل المستخدمين موجودين بالفعل على الجهاز %s") % device.name)
                continue

            if device.connection_mode == 'direct':
                self._handle_direct_sync(device, users_to_add, results)
            elif device.connection_mode == 'iot':
                self._handle_iot_sync(device, users_to_add, results)
            elif device.connection_mode == 'push':
                print(users_to_add,"users_to_addusers_to_addusers_to_add")
                self._handle_push_sync(device, users_to_add, results)
            else:
                results.append(_("نوع الاتصال غير مدعوم للجهاز %s") % device.name)

        if results:
            errors = [r for r in results if 'فشل' in r or 'غير متصل' in r or 'لم يستجب' in r]
            raise UserError("\n".join(errors) if errors else _("تمت مزامنة جميع المستخدمين مع الأجهزة بنجاح."))
        else:
            raise UserError(_("لم يتم تنفيذ أي عملية مزامنة."))

        return {'type': 'ir.actions.act_window_close'}
