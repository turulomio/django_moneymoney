Vue.component('my-datetimepicker', {
    props: {
        value: {
            required: true
        },
        locale:  {
            required:true,
            default: 'en',
        }
    },
    template: `
    <div>
        <v-menu v-model="menu" :close-on-content-click="false" :nudge-right="40" transition="scale-transition" offset-y min-width="auto">
            <template v-slot:activator="{ on, attrs }">
                <v-row justify="center" align="center">
                    <v-text-field v-model="localValue" v-bind="$attrs" prepend-icon="mdi-calendar" readonly v-on="on"  @click="on_text_click"></v-text-field>
                    <v-icon class="ml-1" x-small @click="localValue=''">mdi-backspace</v-icon>
                </v-row>
            </template>
            <v-row>
            <v-date-picker no-title v-model="date" @change="on_date_change()" locale="locale" first-day-of-week="1"></v-date-picker>
            <v-time-picker ref="time" no-title scrollable  format="24hr" v-model="time" use-seconds @click:hour="on_time_click()" @click:minute="on_time_click()" @click:second="on_time_click()" locale="locale"></v-date-picker>
            </v-row>
            <v-btn class="ml-4" color="error" @click="on_close()" >{{buttonCloseText}}</v-btn>
        </v-menu>
    </div>
    `,
    data: function(){
        return {
            menu: false,
            date: "",
            time: "",
            localValue: "",
            buttonCloseText: gettext("Close")
        }
    },
    watch: {
        localValue (newValue) {
            this.$emit('input', newValue)
        },
        value (newValue) {
            this.localValue = newValue
            if (newValue==""){
                this.date=new Date().toISOString().substring(0,10)
                this.time=new Date().toISOString().substring(11,19)
            } else {
                var arr=this.datetimestring2valuestrings(newValue)
                this.date=arr[0]
                this.time=arr[1]
            }
        }
    },
    methods: {
        on_text_click(){
            // Changes to hour selection mode
            if (this.$refs.time) this.$refs.time.selecting=1
        },
        on_close(){
            this.menu=false
        },
        on_date_change(){
            this.localValue=this.valuestrings2datetimestring(this.date,this.time)
        },
        on_time_click(){
            if (this.$refs.time.selecting == 3) {
                this.on_close()
            }
            this.localValue=this.valuestrings2datetimestring(this.date,this.time)
        },
        datetimestring2valuestrings(s){
            return new Array(
                s.substring(0,10),
                s.substring(11,19)
            )
        },
        valuestrings2datetimestring(date_str, time_str){
            if (date_str=="" || time_str==""){
                return moment().format().replace("T", " ")
            }
            var joinDate=new Date(date_str.substring(0,4),date_str.substring(5,7)-1,date_str.substring(8,10),time_str.substring(0,2),time_str.substring(3,5),time_str.substring(6,8))
            return moment(joinDate).format().replace("T", " ")
            
        },
        setWithJsDate(jsdate){
            this.localValue=moment(jsdate).format().replace("T", " ")
        },
        setWithStrings(date_str, time_str){
            this.localValue=this.valuestrings2datetimestring(date_str, time_str)
        }
        
        
    },
    mounted(){
        if (this.value==""){
            this.localValue=this.valuestrings2datetimestring("","")
        }
        
    }
})
