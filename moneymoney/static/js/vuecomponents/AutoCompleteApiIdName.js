
Vue.component('autocompleteapi-idname', {
    props: {
        value: {
            required: true
        },
        url:{
            // Must be defined as `${this.$store.state.apiroot}/api/find/
            // This path can get search=name, and id=id
            required: true
        },
        id:{
            default: "id"
        },
        name:{
            default: "name"
        },
        label:{
            default: "Select an item"
        },
        minchars:{
            type: Number,
            default: 2
        }
    },
    template: `
    <div>
        <v-autocomplete
            v-model="localValue"
            :items="entries"
            :loading="isLoading"
            :search-input.sync="search"
            item-text="name"
            item-value="id"
            no-data-text="You must select a item"
            outlined
            persistent-hint
            :label="label"
            placeholder="Start typing to Search"
            prepend-icon="mdi-database-search"
        ></v-autocomplete>
    </div>
    `,
    data: function(){
        return {
            descriptionLimit: 60,
            entries: [],
            isLoading: false,
            search: null,
            localValue: null
        }
    },
    watch: {
        search (val) {
            // Items have already been loaded
            if (this.search ==null || this.search==""|| this.search.length<this.minchars) return

            // Items have already been requested
            if (this.isLoading) return

            this.isLoading = true

            axios.get(`${this.url}?search=${val}`, myheaders())
            .then((response) => {
                this.entries=response.data
            }, (error) => {
                this.parseResponseError(error)
            })
            .finally(() => (this.isLoading = false));
        },
        localValue (newValue) {
            this.$emit('input', newValue)
            console.log(`LocalValue changed and emited input to ${newValue}`)
        },
        value (newValue) {
            this.localValue = newValue
            console.log(`value changed to ${newValue}`)
        },
    },
    methods: {
        forceValue(force){       
            if (force!=null){
                axios.get(`${this.url}?id=${force}`, myheaders())
                .then((response) => {
                    console.log(response.data)
                    this.entries=response.data
                    this.localValue=response.data.id
                }, (error) => {
                    console.log(error)
                })
                .finally(() => (this.isLoading = false));
            }
        }
    },
    mounted(){
        this.forceValue(this.value)
    }
})
