from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard
    path('', views.dashboard, name='index'),

    # Module HTMX partials
    path('modules/calendar/',      views.module_calendar,   name='module_calendar'),
    path('modules/tasks/',         views.module_tasks,      name='module_tasks'),
    path('modules/notes/',         views.module_notes,      name='module_notes'),
    path('modules/digest/',        views.module_digest,     name='module_digest'),

    # Task actions
    path('tasks/done/',            views.mark_task_done,    name='mark_task_done'),
    path('tasks/add/',             views.add_task,          name='add_task'),

    # Note actions
    path('notes/add/',             views.add_note,          name='add_note'),
    path('notes/<int:pk>/delete/', views.delete_note,       name='delete_note'),

    # Project grab
    path('grab/<int:pk>/',         views.grab_project,      name='grab_project'),

    # Calendar feeds
    path('feeds/',                 views.calendar_feeds_list, name='feeds_list'),
    path('feeds/add/',             views.calendar_feed_add,   name='feed_add'),
    path('feeds/<int:pk>/delete/', views.calendar_feed_delete, name='feed_delete'),
]
