Vue.component('table-investmentoperations', {
    props: {
        items: {
            required: true
        },
        currency_account: {
            required: true,
            default:"EUR",
        },
        currency_investment: {
            required: true,
            default:"EUR",
        },
        currency_user: {
            required: true,
            default:"EUR",
        },
        url_root:{
            required:true
        },
        heterogeneus:{
            type: Boolean,
            required:true,
            default:false
        },
        output:{
            required:true,
            default: "investment",
        },
        locale:{
            required:true,
            default: "es",
        }
    },
    template: `
        <v-data-table dense v-model="selected" :headers="table_headers()" :items="items" class="elevation-1" disable-pagination  hide-default-footer sort-by="datetime" fixed-header :height="$attrs.height" ref="table_o" :key="$attrs.key">
            <template v-slot:[\`item.datetime\`]="{ item,index }">
            <div :ref="index">{{ localtime(item.datetime)}}</div>
            </template>
            <template v-slot:[\`item.price\`]="{ item }">
            {{ currency_string(item.price, currency_investment)}}
            </template>
            
            <template v-slot:[\`item.gross_account\`]="{ item }">
            {{ currency_string(item.gross_account, currency_account)}}
            </template>
            <template v-slot:[\`item.gross_investment\`]="{ item }">
            {{ currency_string(item.gross_investment, currency_investment)}}
            </template>
            <template v-slot:[\`item.gross_user\`]="{ item }">
            {{ currency_string(item.gross_user, currency_user)}}
            </template>
            
            <template v-slot:[\`item.commission\`]="{ item }">
            {{ currency_string(item.commission, currency_investment)}}
            </template>
            <template v-slot:[\`item.taxes\`]="{ item }">
            {{ currency_string(item.taxes, currency_investment)}}
            </template>
            
            <template v-slot:[\`item.net_account\`]="{ item }">
            {{ currency_string(item.net_account, currency_account)}}
            </template>
            <template v-slot:[\`item.net_investment\`]="{ item }">
            {{ currency_string(item.net_investment, currency_investment)}}
            </template>
            <template v-slot:[\`item.net_user\`]="{ item }">
            {{ currency_string(item.net_user, currency_user)}}
            </template>
            
            <template v-slot:[\`item.actions\`]="{ item }">
                <v-icon small class="mr-2" @click="editIO(item)">mdi-pencil</v-icon>
            </template>
        </v-data-table>   
    `,
    data: function(){
        return {
            selected: [],
        }
    },
    computed:{
    },
    methods: {
        // HASN'T MIXIN VIXIBILITY
        currency_string(num, currency, decimals=2){
            return currency_generic_string(num, currency, this.locale,decimals )
        },
        currency_html(num, currency, decimals=2){
            return currency_generic_html(num, currency, this.locale,decimals )
        },
        percentage_string(num, decimals=2){
            return percentage_generic_string(num,this.locale,decimals )
        },
        percentage_html(num, decimals=2){
            return percentage_generic_html(num,this.locale,decimals )
        },
        table_headers(){
            if (this.output=="account"){
                var r= [
                    { text: gettext('Date and time'), value: 'datetime',sortable: true },
                    { text: gettext('Operation'), value: 'operationstypes',sortable: true },
                    { text: gettext('Shares'), value: 'shares',sortable: false, align:"right"},
                    { text: gettext('Price'), value: 'price',sortable: false, align:"right"},
                    { text: gettext('Gross'), value: 'gross_account',sortable: false, align:"right"},
                    { text: gettext('Commission'), value: 'commission',sortable: false, align:"right"},
                    { text: gettext('Taxes'), value: 'taxes',sortable: false, align:"right"},
                    { text: gettext('Net'), value: 'net_account',sortable: false, align:"right"},
                    { text: gettext('Currency factor'), value: 'currency_conversion',sortable: false, align:"right"},
                    { text: gettext('Comment'), value: 'comment',sortable: false},
                    { text: gettext('Actions'), value: 'actions', sortable: false },
                ]
            } else if (this.output=="investment"){                
                var r= [
                    { text: gettext('Date and time'), value: 'datetime',sortable: true },
                    { text: gettext('Operation'), value: 'operationstypes',sortable: true },
                    { text: gettext('Shares'), value: 'shares',sortable: false, align:"right"},
                    { text: gettext('Price'), value: 'price',sortable: false, align:"right"},
                    { text: gettext('Gross'), value: 'gross_investment',sortable: false, align:"right"},
                    { text: gettext('Commission'), value: 'commission',sortable: false, align:"right"},
                    { text: gettext('Taxes'), value: 'taxes',sortable: false, align:"right"},
                    { text: gettext('Net'), value: 'net_investment',sortable: false, align:"right"},
                    { text: gettext('Currency factor'), value: 'currency_conversion',sortable: false, align:"right"},
                    { text: gettext('Comment'), value: 'comment',sortable: false},
                    { text: gettext('Actions'), value: 'actions', sortable: false },
                ]
            } else if (this.output=="user"){
                var r= [
                    { text: gettext('Date and time'), value: 'datetime',sortable: true },
                    { text: gettext('Operation'), value: 'operationstypes',sortable: true },
                    { text: gettext('Shares'), value: 'shares',sortable: false, align:"right"},
                    { text: gettext('Price'), value: 'price',sortable: false, align:"right"},
                    { text: gettext('Gross'), value: 'gross_user',sortable: false, align:"right"},
                    { text: gettext('Commission'), value: 'commission',sortable: false, align:"right"},
                    { text: gettext('Taxes'), value: 'taxes',sortable: false, align:"right"},
                    { text: gettext('Net'), value: 'net_user',sortable: false, align:"right"},
                    { text: gettext('Currency factor'), value: 'currency_conversion',sortable: false, align:"right"},
                    { text: gettext('Comment'), value: 'comment',sortable: false},
                    { text: gettext('Actions'), value: 'actions', sortable: false },
                ]
            }
            
            if (this.currency_investment==this.currency_account){
                r.splice(8,1)
            }
            if (this.heterogeneus==true){
                r.splice(1, 0, { text: gettext('Name'), value: 'name',sortable: true });
            }
            return r
        },
        editIO(item){
            window.location.href=`${this.url_root}investmentoperation/update/${item.id}`
        },
        gotoLastRow(){
           this.$vuetify.goTo(this.$refs[this.items.length-1], { container:  this.$refs.table_o.$el.childNodes[0] }) 
        },
    },
    mounted(){
        this.gotoLastRow()
    }
})
