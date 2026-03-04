import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/views/fields/char/char_field";

export class FieldAudioLink extends CharField {
    static template = "ttb_helpdesk.FieldAudioLink";
}

export const fieldAudioLink = {
    ...charField,
    component: FieldAudioLink,
};

registry.category("fields").add("audio_link", fieldAudioLink);
