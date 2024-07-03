from django.apps import AppConfig

class SearchServicesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'search_services'
    
    def ready(self):
        from elasticsearch_dsl import connections
        from django.conf import settings
        
        ELASTICSEARCH_PASSWORD = settings.ELASTICSEARCH_PASSWORD
        ELASTICSEARCH_HOST = settings.ELASTICSEARCH_HOST
        
        
        #print(ELASTICSEARCH_PASSWORD)
        # Set the connection alias for Elasticsearch DSL
        connections.create_connection(alias='default', hosts=[ELASTICSEARCH_HOST], 
                                      basic_auth=("elastic", ELASTICSEARCH_PASSWORD))
      