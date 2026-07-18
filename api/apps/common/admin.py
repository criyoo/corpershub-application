from django.contrib import admin

from apps.common.models import CourseCategory, CourseField, UniversityCourse


class CourseCategoryInline(admin.TabularInline):
    model = CourseCategory
    extra = 0
    fields = ("name", "sort_order")
    ordering = ("sort_order", "name")


class UniversityCourseInline(admin.TabularInline):
    model = UniversityCourse
    extra = 0
    fields = ("name", "sort_order")
    ordering = ("sort_order", "name")


@admin.register(CourseField)
class CourseFieldAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order", "category_count", "created_at", "updated_at")
    search_fields = ("name",)
    ordering = ("sort_order", "name")
    inlines = (CourseCategoryInline,)

    def category_count(self, obj):
        return obj.categories.count()


@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "field", "sort_order", "course_count", "created_at", "updated_at")
    search_fields = ("name", "field__name")
    list_filter = ("field",)
    ordering = ("field__sort_order", "field__name", "sort_order", "name")
    autocomplete_fields = ("field",)
    inlines = (UniversityCourseInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("field")

    def course_count(self, obj):
        return obj.courses.count()


@admin.register(UniversityCourse)
class UniversityCourseAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "field_name", "sort_order", "created_at", "updated_at")
    search_fields = ("name", "category__name", "category__field__name")
    list_filter = ("category__field", "category")
    ordering = ("category__field__sort_order", "category__sort_order", "sort_order", "name")
    autocomplete_fields = ("category",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("category", "category__field")

    @admin.display(ordering="category__field__name", description="Field")
    def field_name(self, obj):
        return obj.category.field.name
