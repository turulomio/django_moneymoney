Vue.component('my-datepicker', {
    props: {
        value: {
            required: true
        },
    },
    template: `
    <div>
        <v-menu v-model="menu" :close-on-content-click="false" :nudge-right="40" transition="scale-transition" offset-y min-width="auto">
            <template v-slot:activator="{ on, attrs }">
                <v-row justify="center" align="center">
                    <v-text-field v-model="localValue" :name="$attrs.name" :label="$attrs.label" prepend-icon="mdi-calendar" readonly v-bind="attrs" v-on="on"></v-text-field>
                    <v-icon x-small @click="localValue=null">mdi-backspace</v-icon>
                </v-row>
            </template>
            <v-date-picker v-model="localValue" @input="menu = false"></v-date-picker>
        </v-menu>
    </div>
    `,
    data: function(){
        return {
            menu: false,
            localValue: null,
        }
    },
    watch: {
        localValue (newValue) {
            this.$emit('input', newValue)
        },
        value (newValue) {
            this.localValue = newValue
        }
    },
})
