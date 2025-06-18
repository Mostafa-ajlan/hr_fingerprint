import { _t } from "@web/core/l10n/translation";
import { markup, onMounted, useState, onWillUpdateProps, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { handleBiometricIoTConnectionFallbacks2 } from "./iot_implement_action";
import {
    deleteConfirmationMessage,
    ConfirmationDialog,
} from "@web/core/confirmation_dialog/confirmation_dialog";


export class FingerprintUserFormController extends FormController {

    setup() {
        super.setup();
        this.action = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");

        this.state = useState({
            isActive: true, // هل المستخدم نشط
        });

    }

    async saveButtonClicked(params = {}) {
        const record = this.model.root;
        console.log(record, "rrrrrrrrrrrrrrrrrr", this.props.resId)
        const data = record.data;

        const connection_mode = record.data.connection_device_mode;
        this.model.root.context['from_frontend'] = true
        if (connection_mode == "iot" && data.active_user) {
            let uid = undefined;
            if (this.props.resId) {
                const result = await this.orm.read('hr.fingerprint.user', [this.props.resId], ['uid']);
                uid = result[0].uid;
            }

            const iot_record = await this.orm.read('hr.fingerprint.device', [data.device_id[0]], ['iot_device_id']);
            const extraData = {
                name: data.name,
                user_id: data.user_id,
                uid: uid,
                privilege: data.privilege,
                password: data.password,
                group_id: data.group_id,
                card: data.card,
            };
            console.log(extraData, "extraDataextraDataextraData")
            const args = {
                iot_device: iot_record[0].iot_device_id,
                action: 'create_or_update_user',
                extraData: extraData,
            };
            try {

                await handleBiometricIoTConnectionFallbacks2(this.env, this.orm, args);

                this.model.root.context['from_frontend'] = true;
                this.model.root.context['iot_synced'] = true;

                return await super.saveButtonClicked(params);
            } catch (err) {
                this.notification.add(err.message || _t("فشل الاتصال بجهاز IoT"), { type: "danger" });
                return Promise.reject(err);
            }
        } else {
            // direct أو push أو غيرها
            this.model.root.context['from_frontend'] = true;
            return await super.saveButtonClicked(params);
        }
    }

    // async deleteRecord() {
    //     const record = this.model.root;
    //     const data = record.data;
    //     const connection_mode = record.data.connection_device_mode;
    //     this.model.root.context['from_frontend'] = true
    //     if (connection_mode == "iot" && data.active_user) {
    //         const iot_record = await this.orm.read('hr.fingerprint.device', [data.device_id[0]], ['iot_device_id']);
    //         const extraData = {
    //             user_id: data.user_id,
    //             uid: data.uid,
    //         };
    //         const args = {
    //             iot_device: iot_record[0].iot_device_id,
    //             action: 'delete_user',
    //             extraData: extraData,
    //         };
    //         try {

    //             await handleBiometricIoTConnectionFallbacks2(this.env, this.orm, args);
    //             console.log("ddddddddddddddddddddd")

    //             this.model.root.context['iot_synced'] = true;

    //             await super.deleteRecord(...arguments);
    //         } catch (err) {
    //             this.notification.add(err.message || _t("فشل الاتصال بجهاز IoT"), { type: "danger" });
    //             return Promise.reject(err);
    //         }
    //     } else {
    //         await super.deleteRecord(...arguments);
    //     }
    // }

    async deleteRecord() {
        const record = this.model.root;
        const data = record.data;
        const connection_mode = record.data.connection_device_mode;

        const originalDeleteConfirmationDialogProps = this.deleteConfirmationDialogProps;
        this.model.root.context['from_frontend'] = true

        if (connection_mode === "iot" && data.active_user) {
            // Override the confirm callback to include IoT deletion logic
            const customConfirmCallback = async () => {
                const iot_record = await this.orm.read('hr.fingerprint.device', [data.device_id[0]], ['iot_device_id']);
                const extraData = {
                    user_id: data.user_id,
                    uid: data.uid,
                };
                const args = {
                    iot_device: iot_record[0].iot_device_id,
                    action: 'delete_user',
                    extraData: extraData,
                };
                try {
                    await handleBiometricIoTConnectionFallbacks2(this.env, this.orm, args);
                    console.log("User deleted from IoT device successfully.");

                    // If IoT deletion is successful, proceed with Odoo record deletion
                    await originalDeleteConfirmationDialogProps.confirm();
                    this.model.root.context['iot_synced'] = true;
                } catch (err) {
                    this.notification.add(err.message || _t("فشل الاتصال بجهاز IoT"), { type: "danger" });
                    return Promise.reject(err);
                }
            };

            this.dialogService.add(ConfirmationDialog, {
                ...originalDeleteConfirmationDialogProps,
                confirm: customConfirmCallback,
            });
        } else {
            console.log("VBBBBBBBBBBBBBBBBBBBBBBB")
            // For other connection modes, use the original delete logic
            return await super.deleteRecord(...arguments);
        }
    }


    // async updateButtonClicked(params = {}) {
    //     // نفس منطق saveButtonClicked
    //     return await this.saveButtonClicked(params);
    // }

    // async deleteRecord() {
    //     console.log("أـلأـلأـألأـلأـألأـ")
    //     this.dialogService.add(ConfirmationDialog, this.deleteConfirmationDialogProps);
    // }

}

export const fingerprintUserFormController = {
    ...formView,
    Controller: FingerprintUserFormController,
};

registry.category("views").add("fingerprint_user_form", fingerprintUserFormController);


