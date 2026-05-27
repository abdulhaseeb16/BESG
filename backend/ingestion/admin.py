from django.contrib import admin

from .models import ActivityRecord, EmissionFactor, Facility, IngestionBatch, RawRecord, ReviewEvent, SourceSystem, Tenant

admin.site.register(Tenant)
admin.site.register(Facility)
admin.site.register(SourceSystem)
admin.site.register(IngestionBatch)
admin.site.register(RawRecord)
admin.site.register(ActivityRecord)
admin.site.register(ReviewEvent)
admin.site.register(EmissionFactor)
