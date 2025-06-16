import { _t } from "@web/core/l10n/translation";
import { markup, onMounted, useState, onWillUpdateProps, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { handleBiometricIoTConnectionFallbacks2 } from "./iot_implement_action";


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
        const data = record.data;
        const connection_mode = record.data.connection_device_mode;
        this.model.root.context['from_frontend'] = true
        if (connection_mode == "iot" && data.active_user) {
            const iot_record = await this.orm.read('hr.fingerprint.device', [data.device_id[0]], ['iot_device_id']);
            const extraData = {
                name: data.name,
                user_id: data.user_id,
                uid: data.uid,
                privilege: data.privilege,
                password: data.password,
                group_id: data.group_id,
                card: data.card,
            };
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
                console.log("FFFFFFFFFFFFFFFFFFFFFFFFFFFF")
                this.notification.add(err.message || _t("فشل الاتصال بجهاز IoT"), { type: "danger" });
                return Promise.reject(err);
            }
        } else {
            // direct أو push أو غيرها
            this.model.root.context['from_frontend'] = true;
            return await super.saveButtonClicked(params);
        }


    }

    // async saveButtonClicked(params = {}) {
    //     const record = this.model.root;
    //     const data = record.data;
    //     const connection_mode = data.connection_device_mode;
    //     let syncState = 'done';
    //     if (connection_mode === "iot" && data.active_user) {
    //         const iot_record = await this.orm.read('hr.fingerprint.device', [data.device_id[0]], ['iot_device_id']);
    //         const extraData = {
    //             name: data.name,
    //             user_id: data.user_id,
    //             uid: data.uid,
    //             privilege: data.privilege,
    //             password: data.password,
    //             group_id: data.group_id,
    //             card: data.card,
    //         };
    //         const args = {
    //             iot_device: iot_record[0].iot_device_id,
    //             action: 'create_or_update_user',
    //             extraData: extraData,
    //         };
    //         try {
    //             await handleBiometricIoTConnectionFallbacks2(this.env, this.orm, args);
    //             syncState = 'done';
    //         } catch (err) {
    //             this.notification.add(err.message || _t("فشل الاتصال بجهاز IoT. سيتم حفظ المستخدم كمعلق للمزامنة لاحقًا."), { type: "warning" });
    //             syncState = 'pending';
    //         }
    //     }
    //     // احفظ السجل دومًا
    //     this.model.root.context['from_frontend'] = true;
    //     const res = await super.saveButtonClicked(params);
    //     // بعد الحفظ، حدّث حالة المزامنة
    //     if (connection_mode === "iot" && data.id) {
    //         await this.orm.write('hr.fingerprint.user', [data.id], { device_sync_state: syncState });
    //     }
    //     return res;
    // }

    // async updateButtonClicked(params = {}) {
    //     // نفس منطق saveButtonClicked
    //     return await this.saveButtonClicked(params);
    // }

    async deleteRecord() {
        console.log("أـلأـلأـألأـلأـألأـ")
        this.dialogService.add(ConfirmationDialog, this.deleteConfirmationDialogProps);
    }

}

export const fingerprintUserFormController = {
    ...formView,
    Controller: FingerprintUserFormController,
};

registry.category("views").add("fingerprint_user_form", fingerprintUserFormController);