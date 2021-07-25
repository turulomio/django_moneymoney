Vue.component('chart-pie', {
    props: ['items', 'name', 'height','key'],
    template: `
        <div>
            <p v-if="items.length==0">No data to show</p>
            <v-card flat  v-if="items.length>0">
                <v-row no-gutters :style="styleheight">
                    <v-col>
                        <v-chart autoresize :option="options" :key="key"/>
                    </v-col>
                    <v-col v-show="showtable" >
                        <v-data-table dense :headers="tableHeaders"  :items="items" class="elevation-1" disable-pagination  hide-default-footer :sort-by="['value']" :sort-desc="['value']">
                            <template v-slot:[\`item.percentage\`]="{ item, index }">
                                {{ getPercentage(item) }}
                            </template>    
                            <template v-slot:body.append="{headers}">
                                <tr style="background-color: lightgrey">
                                    <td v-for="(header,i) in headers" :key="i">
                                        <div v-if="header.value == 'name'">
                                            Total
                                        </div>
                                        <div v-if="header.value == 'value'" align="right">
                                            {{total}}
                                        </div>
                                        <div v-if="header.value == 'percentage'" align="right">
                                            100 %
                                        </div>
                                    </td>
                                </tr>
                            </template>
                        </v-data-table>
                    </v-col>
                </v-row>       
            </v-card>  
            <v-row>
                <v-col align="center">
                    <v-btn color="primary" @click="buttonClick">{{buttontext}}</v-btn>
                </v-col>
            </v-row>
        </div>
    `,
    data: function () {
        return {
            showtable: false,
            total: 0,
            tableHeaders: [
                { text: 'Name', value: 'name',sortable: true },
                { text: 'Value', value: 'value',sortable: true, align: 'right'},
                { text: 'Percentage', value: 'percentage',sortable: false, align: 'right'},
            ],   
            
        }
    },
    computed:{
        options: function(){
            return {
                tooltip: {
                    trigger: "item",
                    formatter: "{a} <br/>{b} : {c} ({d}%)"
                },
                series: [
                    {
                        name: this.name,
                        type: "pie",
                        radius: "80%",
                        center: ["50%", "50%"],
                        data: this.items,
                        emphasis: {
                            itemStyle: {
                                shadowBlur: 10,
                                shadowOffsetX: 0,
                                shadowColor: "rgba(0, 0, 0, 0.5)"
                            }
                        }
                    }
                ]
            }
        },
        styleheight: function(){
            return `height: ${this.height};`
        },
        buttontext: function(){
            if (this.showtable){
                return "Hide table data"
            } else {
                return "Show table data"
            }
        }
    },
    methods: {
        buttonClick(){
            this.showtable=!this.showtable
            this.key=this.key+1
        },
        getPercentage(item){
            return `${my_round(item.value/this.total*100,2)} %`
            
        }
    },
    mounted(){
        this.total=this.items.reduce((accum,item) => accum + item.value, 0)
    }
})

