/*
Yo need to put items and @selected method

type puede ser redirection or command

<my-menuinline :items="items" @selected="items_selected"></my-menuinline>


            items: [
                {
                    subheader:"Header 1",
                    children: [
                        {
                            name:"Action 1",
                            type: "redirection",
                            command: "www.google.com",
                            icon: "mdi-pencil",
                        },
                    ]
                },
                {
                    subheader:"Header 2",
                    children: [
                        {
                            name:"Action 2",
                            type: "command",
                            command: "command1"
                            icon: "mdi-magnify",
                        },
                    ]
                },
            ]
        items_selected(item){
            if (item.command=="command1"){
		alert("command1")
            }
        }

*/

Vue.component('my-menuinline', {
    props: {
        items: {
            required: true
        },
    },
    template: `

<v-menu offset-y>
    <template v-slot:activator="{ on, attrs }">
        <v-btn text dark v-bind="attrs" v-on="on" style="color:darkgrey;">
            <v-icon>mdi-menu</v-icon>
        </v-btn>
    </template>
    <v-list dense subheader >
        <div v-for="(subheader,indexsubheader) in items" :key="indexsubheader" inset>
            <v-subheader inset>{{ subheader.subheader }}</v-subheader>
            <v-list-item v-for="(item, index) in subheader.children" :key="index" @click="parseCommand(item)">
            <v-list-item-icon>
                <v-icon v-text="item.icon"></v-icon>
            </v-list-item-icon>
                {{ item.name }}
            </v-list-item>
            <v-divider></v-divider>
        </div>
    </v-list>
</v-menu>
    `,
    data: function(){
        return {
        }
    },

    methods: {
        parseCommand(item){
            if (item.type=="function") {
                this.$emit("selected", item)
            } else if (item.type=="redirection") {
                window.location.replace(item.command)
            }
        },
    },
})
