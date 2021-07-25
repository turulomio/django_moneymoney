Vue.component('table-investmentoperationscurrent', {
    props: {
        items: {
            required: true
        },
        currency_account: {
            required: true,
            default:"EUR"
        },
        currency_investment: {
            required: true,
            default:"EUR"
        },
        currency_user: {
            required: true,
            default:"EUR"
        },
        url_root:{
            required:true
        },
        heterogeneus:{
            type: Boolean,
            required:true,
            default:false,
        },
        output:{
            required:true,
            default:"account",
        },
        locale:{
            required:true,
            default: "es",
        }
    },
    template: `
        <v-data-table dense :headers="table_headers()" :items="items" class="elevation-1" disable-pagination  hide-default-footer sort-by="datetime" fixed-header :height="$attrs.height" :key="$attrs.key">
            <template v-slot:[\`item.datetime\`]="{ item }" >
            {{ localtime(item.datetime)}}
            </template>          
            <template v-slot:[\`item.gains_gross_account\`]="{ item }">
                <div v-html="currency(item.gains_gross_account)"></div>
            </template>        
            <template v-slot:[\`item.gains_gross_investment\`]="{ item }">
                <div v-html="currency(item.gains_gross_investment)"></div>
            </template>  
            <template v-slot:[\`item.gains_gross_user\`]="{ item }">
                <div v-html="currency(item.gains_gross_user)"></div>
            </template>  
            
            <template v-slot:[\`item.price_account\`]="{ item }">
                <div v-html="currency(item.price_account)"></div>
            </template>  
            <template v-slot:[\`item.price_investment\`]="{ item }">
                <div v-html="currency(item.price_investment)"></div>
            </template>  
            <template v-slot:[\`item.price_user\`]="{ item }">
                <div v-html="currency(item.price_user)"></div>
            </template>  
            
            <template v-slot:[\`item.invested_account\`]="{ item }">
                <div v-html="currency(item.invested_account)"></div>
            </template>  
            <template v-slot:[\`item.invested_investment\`]="{ item }">
                <div v-html="currency(item.invested_investment)"></div>
            </template>
            <template v-slot:[\`item.invested_user\`]="{ item }">
                <div v-html="currency(item.invested_user)"></div>
            </template> 
            
            <template v-slot:[\`item.balance_account\`]="{ item }">
                <div v-html="currency(item.balance_account)"></div>
            </template>  
            <template v-slot:[\`item.balance_investment\`]="{ item }">
                <div v-html="currency(item.balance_investment)"></div>
            </template>  
            <template v-slot:[\`item.balance_user\`]="{ item }">
                <div v-html="currency(item.balance_user)"></div>
            </template>  
            
            <template v-slot:[\`item.percentage_annual_investment\`]="{ item }">
                <div v-html="percentage_html(item.percentage_annual_investment)"></div>
            </template>
            <template v-slot:[\`item.percentage_apr_investment\`]="{ item }">
                <div v-html="percentage_html(item.percentage_apr_investment)"></div>
            </template>
            <template v-slot:[\`item.percentage_total_investment\`]="{ item }">
                <div v-html="percentage_html(item.percentage_total_investment)"></div>
            </template>            
            <template v-slot:body.append="{headers}">
                <tr style="background-color: GhostWhite" ref="lr">
                    <td v-for="(header,i) in headers" :key="i" >
                        <div v-if="header.value == 'datetime'">
                            Total
                        </div>
                        <div v-if="header.value == 'shares'" align="right">
                            <div v-html="items.reduce((accum,item) => accum + item.shares, 0)"></div>
                        </div>
                        
                        <div v-if="header.value == 'price_account'" align="right">
                            <div v-html="currency(listobjects_average_ponderated(items,'price_account', 'shares'))"></div>
                        </div>
                        <div v-if="header.value == 'price_investment'" align="right">
                            <div v-html="currency(listobjects_average_ponderated(items,'price_investment', 'shares'))"></div>
                        </div>
                        <div v-if="header.value == 'price_user'" align="right">
                            <div v-html="currency(listobjects_average_ponderated(items,'price_user', 'shares'))"></div>
                        </div>
                        
                        
                        <div v-if="header.value == 'gains_gross_account'" align="right">
                            <div v-html="currency(items.reduce((accum,item) => accum + item.gains_gross_account, 0))"></div>
                        </div>
                        <div v-if="header.value == 'gains_gross_investment'" align="right">
                            <div v-html="currency(items.reduce((accum,item) => accum + item.gains_gross_investment, 0))"></div>
                        </div>
                        <div v-if="header.value == 'gains_gross_user'" align="right">
                            <div v-html="currency(items.reduce((accum,item) => accum + item.gains_gross_user, 0))"></div>
                        </div>
                        
                        <div v-if="header.value == 'invested_account'" align="right">
                            <div v-html="currency(items.reduce((accum,item) => accum + item.invested_account, 0))"></div>
                        </div>
                        <div v-if="header.value == 'invested_investment'" align="right">
                            <div v-html="currency(items.reduce((accum,item) => accum + item.invested_investment, 0))"></div>
                        </div>
                        <div v-if="header.value == 'invested_user'" align="right">
                            <div v-html="currency(items.reduce((accum,item) => accum + item.invested_user, 0))"></div>
                        </div>
                        
                        <div v-if="header.value == 'balance_account'" align="right">
                            <div v-html="currency(items.reduce((accum,item) => accum + item.balance_account, 0))"></div>
                        </div>
                        <div v-if="header.value == 'balance_investment'" align="right">
                            <div v-html="currency(items.reduce((accum,item) => accum + item.balance_investment, 0))"></div>
                        </div>
                        <div v-if="header.value == 'balance_user'" align="right">
                            <div v-html="currency(items.reduce((accum,item) => accum + item.balance_user, 0))"></div>
                        </div>
                    </td>
                </tr>
                
            </template>
        </v-data-table>   
    `,
    data: function(){
        return {
        }
    },
    methods: {
        // HASN'T MIXIN VIXIBILITY
//         currency_string(num, currency, decimals=2){
//             return currency_generic_string(num, currency, this.locale,decimals )
//         },
//         currency_html(num, currency, decimals=2){
//             return currency_generic_html(num, currency, this.locale,decimals )
//         },
        percentage_string(num, decimals=2){
            return percentage_generic_string(num,this.locale,decimals )
        },
        percentage_html(num, decimals=2){
            return percentage_generic_html(num,this.locale,decimals )
        },
        currency(value){
            if (this.output=="account"){
                return currency_generic_html(value, this.currency_account, this.locale)
            } else if (this.output=="investment"){
                return currency_generic_html(value, this.currency_investment, this.locale)
            } else if (this.output=="user"){
                return currency_generic_html(value, this.currency_user, this.locale)
            }
        },
        table_headers(){
            if (this.output=="account"){
                var r= [
                    { text: gettext('Date and time'), value: 'datetime',sortable: true },
                    { text: gettext('Operation'), value: 'operationstypes',sortable: true },
                    { text: gettext('Shares'), value: 'shares',sortable: false, align:"right"},
                    { text: gettext('Price'), value: 'price_account',sortable: false, align:"right"},
                    { text: gettext('Invested'), value: 'invested_account',sortable: false, align:"right"},
                    { text: gettext('Balance'), value: 'balance_account',sortable: false, align:"right"},
                    { text: gettext('Gross gains'), value: 'gains_gross_account',sortable: false, align:"right"},
                    { text: gettext('% annual'), value: 'percentage_annual_investment',sortable: false, align:"right"},
                    { text: gettext('% APR'), value: 'percentage_apr_investment',sortable: false, align:"right"},
                    { text: gettext('% Total'), value: 'percentage_total_investment',sortable: false, align:"right"},
                ]
            } else if (this.output=="investment"){
                var r= [
                    { text: gettext('Date and time'), value: 'datetime',sortable: true },
                    { text: gettext('Operation'), value: 'operationstypes',sortable: true },
                    { text: gettext('Shares'), value: 'shares',sortable: false, align:"right"},
                    { text: gettext('Price'), value: 'price_investment',sortable: false, align:"right"},
                    { text: gettext('Invested'), value: 'invested_investment',sortable: false, align:"right"},
                    { text: gettext('Balance'), value: 'balance_investment',sortable: false, align:"right"},
                    { text: gettext('Gross gains'), value: 'gains_gross_investment',sortable: false, align:"right"},
                    { text: gettext('% annual'), value: 'percentage_annual_investment',sortable: false, align:"right"},
                    { text: gettext('% TAE'), value: 'percentage_apr_investment',sortable: false, align:"right"},
                    { text: gettext('% Total'), value: 'percentage_total_investment',sortable: false, align:"right"},
                ]
            } else if (this.output=="user"){
                var r= [
                    { text: gettext('Date and time'), value: 'datetime',sortable: true },
                    { text: gettext('Operation'), value: 'operationstypes',sortable: true },
                    { text: gettext('Shares'), value: 'shares',sortable: false, align:"right"},
                    { text: gettext('Price'), value: 'price_user',sortable: false, align:"right"},
                    { text: gettext('Invested'), value: 'invested_user',sortable: false, align:"right"},
                    { text: gettext('Balance'), value: 'balance_user',sortable: false, align:"right"},
                    { text: gettext('Gross gains'), value: 'gains_gross_user',sortable: false, align:"right"},
                    { text: gettext('% annual'), value: 'percentage_annual_user',sortable: false, align:"right"},
                    { text: gettext('% TAE'), value: 'percentage_apr_user',sortable: false, align:"right"},
                    { text: gettext('% Total'), value: 'percentage_total_user',sortable: false, align:"right"},
                ]
            }            
            if (this.heterogeneus==true){
                r.splice(1, 0, { text: gettext('Name'), value: 'name',sortable: true });
            }
            return r
        },
        gotoLastRow(){
           this.$vuetify.goTo(this.$refs.lr, { container:  ".v-data-table__wrapper" }) 
        },
    },
    mounted(){
        this.gotoLastRow()
    }
})
