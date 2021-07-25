Vue.component('table-investmentoperationshistorical', {
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
        currency_user:{
            required: true,
            default:"EUR"
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
            default:"account",
        },
        locale:{
            required:true,
            default: "es",
        }
    },
    template: `
        <v-data-table dense :headers="table_headers()" :items="items" class="elevation-1" disable-pagination  hide-default-footer sort-by="dt_end" fixed-header :height="$attrs.height"  :key="$attrs.key" ref="table">
            <template v-slot:[\`item.dt_end\`]="{ item }">
            {{ localtime(item.dt_end)}}
            </template>
            <template v-slot:[\`item.gross_start_user\`]="{ item }">
                <div v-html="currency(item.gross_start_user)"></div>
            </template>
            <template v-slot:[\`item.gross_end_user\`]="{ item }">
                <div v-html="currency(item.gross_end_user)"></div>
            </template>
            <template v-slot:[\`item.gains_gross_user\`]="{ item }">
                <div v-html="currency(item.gains_gross_user)"></div>
            </template>
            <template v-slot:[\`item.commissions_user\`]="{ item }">
                <div v-html="currency(item.commissions_user)"></div>
            </template>
            <template v-slot:[\`item.taxes_user\`]="{ item }">
                <div v-html="currency(item.taxes_user)"></div>
            </template>
            <template v-slot:[\`item.gains_net_user\`]="{ item }">
                <div v-html="currency(item.gains_net_user)"></div>
            </template>
            
            
            <template v-slot:[\`item.gross_start_account\`]="{ item }">
                <div v-html="currency(item.gross_start_account)"></div>
            </template>
            <template v-slot:[\`item.gross_end_account\`]="{ item }">
                <div v-html="currency(item.gross_end_account)"></div>
            </template>
            <template v-slot:[\`item.gains_gross_account\`]="{ item }">
                <div v-html="currency(item.gains_gross_account)"></div>
            </template>
            <template v-slot:[\`item.commissions_account\`]="{ item }">
                <div v-html="currency(item.commissions_account)"></div>
            </template>
            <template v-slot:[\`item.taxes_account\`]="{ item }">
                <div v-html="currency(item.taxes_account)"></div>
            </template>
            <template v-slot:[\`item.gains_net_account\`]="{ item }">
                <div v-html="currency(item.gains_net_account)"></div>
            </template>
            
            
            <template v-slot:[\`item.gross_start_investment\`]="{ item }">
                <div v-html="currency(item.gross_start_investment)"></div>
            </template>
            <template v-slot:[\`item.gross_end_investment\`]="{ item }">
                <div v-html="currency(item.gross_end_investment)"></div>
            </template>
            <template v-slot:[\`item.gains_gross_investment\`]="{ item }" >
                <div v-html="currency(item.gains_gross_investment)"></div>
            </template>
            <template v-slot:[\`item.commissions_investment\`]="{ item }">
                <div v-html="currency(item.commissions_investment)"></div>
            </template>
            <template v-slot:[\`item.taxes_investment\`]="{ item }">
                <div v-html="currency(item.taxes_investment)"></div>
            </template>
            <template v-slot:[\`item.gains_net_investment\`]="{ item }">
                <div v-html="currency(item.gains_net_investment)"></div>
            </template>           
            <template v-slot:body.append="{headers}">
                <tr style="background-color: GhostWhite" ref="lastrow">
                    <td v-for="(header,i) in headers" :key="i" >
                        <div v-if="header.value == 'dt_end'">
                            Total
                        </div>
                        
                        <div v-if="header.value == 'gains_gross_investment'" align="right">
                            <div v-html="currency(listobjects_sum(items,'gains_gross_investment'))"></div>
                        </div>
                        <div v-if="header.value == 'gains_gross_account'" align="right">
                            <div v-html="currency(listobjects_sum(items,'gains_gross_account'))"></div>
                        </div>
                        <div v-if="header.value == 'gains_gross_user'" align="right">
                            <div v-html="currency(listobjects_sum(items,'gains_gross_user'))"></div>
                        </div>
                        
                        <div v-if="header.value == 'gains_net_investment'" align="right">
                            <div v-html="currency(listobjects_sum(items,'gains_net_investment'))"></div>
                        </div>
                        <div v-if="header.value == 'gains_net_account'" align="right">
                            <div v-html="currency(listobjects_sum(items,'gains_net_account'))"></div>
                        </div>
                        <div v-if="header.value == 'gains_net_user'" align="right">
                            <div v-html="currency(listobjects_sum(items,'gains_net_user'))"></div>
                        </div>
                        
                        
                        <div v-if="header.value == 'commissions_investment'" align="right">
                            <div v-html="currency(listobjects_sum(items,'commissions_investment'))"></div>
                        </div>
                        <div v-if="header.value == 'commissions_account'" align="right">
                            <div v-html="currency(listobjects_sum(items,'commissions_account'))"></div>
                        </div>
                        
                        
                        <div v-if="header.value == 'taxes_investment'" align="right">
                            <div v-html="currency(listobjects_sum(items,'taxes_investment'))"></div>
                        </div>
                        <div v-if="header.value == 'taxes_account'" align="right">
                            <div v-html="currency(listobjects_sum(items,'taxes_account'))"></div>
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
        currency(value){
            if (this.output=="account"){
                return currency_generic_html(value, this.currency_account,this.locale)
            } else if (this.output=="investment"){
                return currency_generic_html(value, this.currency_investment,this.locale)
            } else if (this.output=="user"){
                return currency_generic_html(value, this.currency_user,this.locale)
            }
        },
        table_headers(){
            if (this.output=="account"){
                var r= [
                    { text: gettext('Date and time'), value: 'dt_end',sortable: true },
                    { text: gettext('Years'), value: 'years',sortable: true },
                    { text: gettext('Operation'), value: 'operationstypes',sortable: true },
                    { text: gettext('Shares'), value: 'shares',sortable: false, align:"right"},
                    { text: gettext('Gross start'), value: 'gross_start_account',sortable: false, align:"right"},
                    { text: gettext('Gross end'), value: 'gross_end_account',sortable: false, align:"right"},
                    { text: gettext('Gains gross'), value: 'gains_gross_account',sortable: false, align:"right"},
                    { text: gettext('Commission'), value: 'commissions_account',sortable: false, align:"right"},
                    { text: gettext('Taxes'), value: 'taxes_account',sortable: false, align:"right"},
                    { text: gettext('Gains'), value: 'gains_net_account',sortable: false, align:"right"},
                ]
            } else if (this.output=="investment"){
                var r= [
                    { text: gettext('Date and time'), value: 'dt_end',sortable: true },
                    { text: gettext('Years'), value: 'years',sortable: true },
                    { text: gettext('Operation'), value: 'operationstypes',sortable: true },
                    { text: gettext('Shares'), value: 'shares',sortable: false, align:"right"},
                    { text: gettext('Gross start'), value: 'gross_start_investment',sortable: false, align:"right"},
                    { text: gettext('Gross end'), value: 'gross_end_investment',sortable: false, align:"right"},
                    { text: gettext('Gains gross'), value: 'gains_gross_investment',sortable: false, align:"right"},
                    { text: gettext('Commission'), value: 'commissions_investment',sortable: false, align:"right"},
                    { text: gettext('Taxes'), value: 'taxes_investment',sortable: false, align:"right"},
                    { text: gettext('Gains'), value: 'gains_net_investment',sortable: false, align:"right"},
                ]
            } else if (this.output=="user"){
                var r= [
                    { text: gettext('Date and time'), value: 'dt_end',sortable: true },
                    { text: gettext('Years'), value: 'years',sortable: true },
                    { text: gettext('Operation'), value: 'operationstypes',sortable: true },
                    { text: gettext('Shares'), value: 'shares',sortable: false, align:"right"},
                    { text: gettext('Gross start'), value: 'gross_start_user',sortable: false, align:"right"},
                    { text: gettext('Gross end'), value: 'gross_end_user',sortable: false, align:"right"},
                    { text: gettext('Gains gross'), value: 'gains_gross_user',sortable: false, align:"right"},
                    { text: gettext('Commission'), value: 'commissions_user',sortable: false, align:"right"},
                    { text: gettext('Taxes'), value: 'taxes_user',sortable: false, align:"right"},
                    { text: gettext('Gains'), value: 'gains_net_user',sortable: false, align:"right"},
                ] 
            }
            if (this.heterogeneus==true){
                r.splice(1, 0, { text: gettext('Name'), value: 'name',sortable: true });
            }
            return r
        },
        gotoLastRow(){
           this.$vuetify.goTo(this.$refs.lastrow, { container:  this.$refs.table.$el.childNodes[0] }) 
        },
    },
    mounted(){
        this.gotoLastRow()
    }
})
