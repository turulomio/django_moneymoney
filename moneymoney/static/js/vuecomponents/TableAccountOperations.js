Vue.component('table-accountoperations', {
    props: {
        items: {
            required: true
        },
        currency_account: {
            required: true
        },
        url_root:{
            required:true
        },
        homogeneous:{
            required:true,
            default:true,
        },
        locale:{
            required:true,
            default: "es",
        }
    },
    template: `
        <v-data-table dense :headers="table_headers()" :items="items" class="elevation-1" disable-pagination  hide-default-footer sort-by="datetime" fixed-header v-bind="$attrs"  :ref="$vnode.tag">
            <template v-slot:[\`item.datetime\`]="{ item }" >
            {{ localtime(item.datetime)}}
            </template>      
            <template v-slot:[\`item.amount\`]="{ item }">
                <div v-html="currency(item.amount)"></div>
            </template>   
            <template v-slot:[\`item.balance\`]="{ item }">
                <div v-html="currency(item.balance)"></div>
            </template>   
            <template v-slot:[\`item.actions\`]="{ item }">
                <v-icon small class="mr-2" @click="editAO(item)">mdi-pencil</v-icon>
                <v-icon small class="mr-2" @click="deleteAO(item)">mdi-delete</v-icon>
            </template>
            <template v-slot:body.append="{headers}">
                <tr style="background-color: GhostWhite">
                    <td v-for="(header,i) in headers" :key="i" >
                        <div v-if="header.value == 'datetime'">
                            Total
                        </div>
                        <div v-if="header.value == 'amount'">
                            <div class="text-right" v-html="currency(listobjects_sum(items,'amount'))"></div>
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
            return currency_generic_html(value, this.currency_account, this.locale)
        },
        editAO(item){
            window.location.href=`${this.url_root}accountoperation/update/${item.id}`
        },
        deleteAO(item){
            window.location.href=`${this.url_root}accountoperation/delete/${item.id}`
        },
        table_headers(){
            return [
                { text: gettext('Date and time'), value: 'datetime', sortable: true },
                { text: gettext('Concept'), value: 'concepts', sortable: true },
                { text: gettext('Amount'), value: 'amount', sortable: false, align:"right"},
                { text: gettext('Balance'), value: 'balance', sortable: false, align:"right"},
                { text: gettext('Comment'), value: 'comment', sortable: true },
                { text: gettext('Actions'), value: 'actions', sortable: false },
            ]
        },
        gotoLastRow(){
           this.$vuetify.goTo(100000, { container:  this.$refs[this.$vnode.tag].$el.childNodes[0] ,duration: 500}) 
        },
    },
})
