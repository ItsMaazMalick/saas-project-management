import django_filters
from .models import Task, TaskPriority, TaskStatus


class TaskFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=TaskStatus.choices)
    priority = django_filters.ChoiceFilter(choices=TaskPriority.choices)
    project = django_filters.UUIDFilter(field_name="project_id")
    assigned_to = django_filters.UUIDFilter(field_name="assigned_to_id")
    due_date_before = django_filters.DateFilter(field_name="due_date", lookup_expr="lte")
    due_date_after = django_filters.DateFilter(field_name="due_date", lookup_expr="gte")

    class Meta:
        model = Task
        fields = ("status", "priority", "project", "assigned_to")
