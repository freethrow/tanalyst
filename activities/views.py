from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Activity
from .forms import ActivityForm


def activity_list(request):
    """List all activities with pagination and filtering."""
    activities = Activity.objects.all()

    # Filter by year
    year_filter = request.GET.get('anno')
    if year_filter:
        activities = activities.filter(anno=year_filter)

    # Filter by sector
    sector_filter = request.GET.get('settore')
    if sector_filter:
        activities = activities.filter(settore__icontains=sector_filter)

    # Filter by office
    office_filter = request.GET.get('ufficio')
    if office_filter:
        activities = activities.filter(ufficio__icontains=office_filter)

    # Pagination
    paginator = Paginator(activities, 20)  # Show 20 activities per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get unique years and offices for filters
    years = Activity.objects.values_list('anno', flat=True).distinct().order_by('-anno')
    offices = Activity.objects.values_list('ufficio', flat=True).distinct().order_by('ufficio')

    context = {
        'page_obj': page_obj,
        'years': years,
        'offices': offices,
        'current_year': year_filter,
        'current_sector': sector_filter,
        'current_office': office_filter,
    }
    return render(request, 'activities/activity_list.html', context)


def activity_detail(request, pk):
    """View a single activity."""
    activity = get_object_or_404(Activity, pk=pk)
    context = {'activity': activity}
    return render(request, 'activities/activity_detail.html', context)


def activity_create(request):
    """Create a new activity."""
    if request.method == 'POST':
        form = ActivityForm(request.POST)
        if form.is_valid():
            activity = form.save()
            messages.success(request, f'Activity "{activity.nome_iniziativa}" created successfully!')
            return redirect('activities:activity_detail', pk=activity.pk)
    else:
        form = ActivityForm()

    context = {'form': form, 'action': 'Create'}
    return render(request, 'activities/activity_form.html', context)


def activity_update(request, pk):
    """Update an existing activity."""
    activity = get_object_or_404(Activity, pk=pk)

    if request.method == 'POST':
        form = ActivityForm(request.POST, instance=activity)
        if form.is_valid():
            activity = form.save()
            messages.success(request, f'Activity "{activity.nome_iniziativa}" updated successfully!')
            return redirect('activities:activity_detail', pk=activity.pk)
    else:
        form = ActivityForm(instance=activity)

    context = {'form': form, 'activity': activity, 'action': 'Update'}
    return render(request, 'activities/activity_form.html', context)


def activity_delete(request, pk):
    """Delete an activity."""
    activity = get_object_or_404(Activity, pk=pk)

    if request.method == 'POST':
        nome = activity.nome_iniziativa
        activity.delete()
        messages.success(request, f'Activity "{nome}" deleted successfully!')
        return redirect('activities:activity_list')

    context = {'activity': activity}
    return render(request, 'activities/activity_confirm_delete.html', context)
