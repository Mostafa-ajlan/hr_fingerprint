# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
import random
import requests
import time

from odoo import _, api, fields, models
from odoo.exceptions import UserError

TIMEOUT = 20


class AddFingerprintDevice(models.TransientModel):
    _name = 'add.fingerprint.device'
    _description = 'Add Fingerprint Device wizard'

    name = fields.Char(string='Device Display Name', required=True, tracking=True)
    connection_mode = fields.Selection([
        ('iot', 'IoT Box'),
        ('direct', 'Direct'),
        ('push', 'Push'),
    ], string='Connection Mode', default="direct", required=True, tracking=True)

    # Fields for connection type selection
    connection_type = fields.Selection([
        ('network', 'Network'),
        ('RS232/RS485', 'Serial'),
        ('usb', 'USB'),
    ], string='Connection Type', default='network', required=True, tracking=True)

    ip_address = fields.Char(string='IP Address', tracking=True)
    port = fields.Integer(string='Port', default=4370, tracking=True)
    serial_number = fields.Char(string='Serial Number', tracking=True)
    # For Network connection
    protocol = fields.Selection([
        ('tcp', 'TCP/IP'),
        ('udp', 'UDP')
    ], string='Protocol', default='tcp', tracking=True)
    connection_timeout = fields.Integer(string='Connection Timeout (seconds)', default=30, tracking=True)

    # IoT Box connection fields
    iot_device_id = fields.Many2one(
        'iot.device', 
        string='IoT Device',
        domain=lambda self: self._get_iot_device_domain(),
        tracking=True
    )
    # iot_device_id = fields.Many2one(
    #     'iot.device', 
    #     string='IoT Device',
    #     domain="[('type', '=', 'biometric')]",
    #     tracking=True
    # )
    
    iot_status = fields.Selection(
        selection=[
            ('connected', 'Connected'),
            ('disconnected', 'Disconnected'),
            ('not_applicable', 'N/A')
        ],
        string='IoT Connection Status',
        compute='_compute_iot_status',
        default='not_applicable'  # ⚠️ إضافة قيمة افتراضية
    )

    def _get_iot_device_domain(self):
        used_ids = self.env['hr.fingerprint.device'].search([]).mapped('iot_device_id.id')
        return [('type', '=', 'biometric'), ('id', 'not in', used_ids)]
    
    # def _get_iot_device_domain(self):
    #     used_ids = self.env['hr.fingerprint.device'].search([]).mapped('iot_device_id.id')
    #     print(used_ids, "used_ids")
    #     return f"[('type', '=', 'biometric'),('id', 'not in',{used_ids})]"
    
    @api.depends('connection_mode', 'iot_device_id.connected')
    def _compute_iot_status(self):
        for device in self:
            if device.connection_mode == 'iot'  and device.iot_device_id:
                device.iot_status = 'connected' if device.iot_device_id.connected else 'disconnected'
            else:
                device.iot_status = 'not_applicable'

    def save_device(self):
        print("save_device")
        return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'info',
                    'message': _("Using Pairing Code to connect..."),
                    'sticky': False,
                    'params': {
                        'next': {'type': 'ir.actions.act_window_close'},
                    }
                },
            }            

