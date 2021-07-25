from django.core.management.base import BaseCommand
from os import system
from shutil import copy

class Command(BaseCommand):
    help = 'Update reusing project'

    def handle(self, *args, **options):
        system("npm update")
        # JS
        copy("node_modules/@vue/composition-api/dist/vue-composition-api.prod.js", "money/static/js/")
        copy("node_modules/chart.js/dist/Chart.min.js", "money/static/js/")
        copy("node_modules/bootstrap/dist/js/bootstrap.js", "money/static/js/")
        copy("node_modules/bootstrap/dist/js/bootstrap.js.map", "money/static/js/")
        copy("node_modules/echarts/dist/echarts.min.js", "money/static/js/")
        copy("node_modules/vue-echarts/dist/index.umd.min.js", "money/static/js/")
        copy("node_modules/vue-echarts/dist/index.umd.min.js.map", "money/static/js/")
        copy("node_modules/jquery-datetimepicker/build/jquery.datetimepicker.full.min.js", "money/static/js/")
        copy("node_modules/jquery/dist/jquery.js", "money/static/js/")
        copy("node_modules/moment-timezone/builds/moment-timezone-with-data.js", "money/static/js/")
        copy("node_modules/moment/moment.js", "money/static/js/")
        #print("Warning: Using moment.js from dist breakes moment-timezone. So I use from root directory")
        copy("node_modules/tabulator-tables/dist/js/tabulator.min.js", "money/static/js/")
        copy("node_modules/vue/dist/vue.min.js", "money/static/js/")
        copy("node_modules/vuetify/dist/vuetify.min.js", "money/static/js/")
        copy("node_modules/xlsx/dist/xlsx.full.min.js", "money/static/js/")
        copy("node_modules/axios/dist/axios.min.js", "money/static/js/")
        copy("node_modules/axios/dist/axios.min.map", "money/static/js/")

        # CSS
        copy("node_modules/chart.js/dist/Chart.css", "money/static/css/")
        copy("node_modules/bootstrap/dist/css/bootstrap.css", "money/static/css/")
        copy("node_modules/bootstrap/dist/css/bootstrap.css.map", "money/static/css/")
        copy("node_modules/jquery-datetimepicker/build/jquery.datetimepicker.min.css", "money/static/css/")
        copy("node_modules/tabulator-tables/dist/css/tabulator.min.css", "money/static/css/")
        copy("node_modules/tabulator-tables/dist/css/tabulator.min.css.map", "money/static/css/")
        copy("node_modules/vuetify/dist/vuetify.min.css", "money/static/css/")
        copy("node_modules/@mdi/font/css/materialdesignicons.min.css", "money/static/css/")
        copy("node_modules/@mdi/font/fonts//materialdesignicons-webfont.woff2", "money/static/fonts/")
