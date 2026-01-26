from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from .models import Activity
from .forms import ActivityForm
import json
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
from weasyprint import HTML
import io


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


@require_POST
def generate_excel_report(request):
    """Generate Excel report for selected activities."""
    try:
        # Parse activity IDs from request
        activity_ids_json = request.POST.get('activity_ids', '[]')
        activity_ids = json.loads(activity_ids_json)

        if not activity_ids:
            messages.error(request, 'No activities selected for report generation.')
            return redirect('activities:activity_list')

        # Fetch activities from database
        activities = Activity.objects.filter(id__in=activity_ids).order_by('-anno', '-mese')

        if not activities.exists():
            messages.error(request, 'No activities found with the selected IDs.')
            return redirect('activities:activity_list')

        # Create workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Activities Report"

        # Define styles
        header_font = Font(bold=True, size=12, color="FFFFFF")
        header_fill = PatternFill(start_color="EB6440", end_color="EB6440", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        cell_alignment = Alignment(vertical="top", wrap_text=True)
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # Add title
        ws.merge_cells('A1:H1')
        title_cell = ws['A1']
        title_cell.value = f"Activities Report - Generated on {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        title_cell.font = Font(bold=True, size=14)
        title_cell.alignment = Alignment(horizontal="center")
        ws.row_dimensions[1].height = 25

        # Add headers (row 3)
        headers = ['Date', 'Type', 'Initiative', 'City', 'Sector', 'Office', 'Responsible', 'Description']
        ws.append([])  # Empty row 2
        ws.append(headers)

        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = border

        # Set column widths
        column_widths = [12, 15, 30, 15, 20, 15, 20, 40]
        for col_num, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(col_num)].width = width

        # Add activity data
        for activity in activities:
            row_data = [
                f"{activity.mese}/{activity.anno}",
                activity.tipo or "",
                activity.nome_iniziativa or "",
                activity.citta or "",
                activity.settore or "",
                activity.ufficio or "",
                activity.responsabile_iniziativa or "",
                activity.descrizione or ""
            ]
            ws.append(row_data)

            # Apply styling to the row
            row_num = ws.max_row
            for col_num in range(1, len(headers) + 1):
                cell = ws.cell(row=row_num, column=col_num)
                cell.alignment = cell_alignment
                cell.border = border

        # Freeze header rows
        ws.freeze_panes = 'A4'

        # Set row height for title
        ws.row_dimensions[3].height = 30

        # Save to BytesIO
        excel_file = io.BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)

        # Create HTTP response
        response = HttpResponse(
            excel_file.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"activities_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except json.JSONDecodeError:
        messages.error(request, 'Invalid activity IDs format.')
        return redirect('activities:activity_list')
    except Exception as e:
        messages.error(request, f'Error generating Excel report: {str(e)}')
        return redirect('activities:activity_list')


@require_POST
def generate_pdf_report(request):
    """Generate PDF report for selected activities using WeasyPrint."""
    try:
        # Parse activity IDs from request
        activity_ids_json = request.POST.get('activity_ids', '[]')
        activity_ids = json.loads(activity_ids_json)

        if not activity_ids:
            messages.error(request, 'No activities selected for report generation.')
            return redirect('activities:activity_list')

        # Fetch activities from database
        activities = Activity.objects.filter(id__in=activity_ids).order_by('-anno', '-mese')

        if not activities.exists():
            messages.error(request, 'No activities found with the selected IDs.')
            return redirect('activities:activity_list')

        # Render HTML template
        context = {
            'activities': activities,
            'generated_date': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'total_count': activities.count()
        }

        html_string = render_to_string('activities/activities_report_pdf.html', context)

        # Generate PDF
        pdf_file = HTML(string=html_string).write_pdf()

        # Create HTTP response
        response = HttpResponse(pdf_file, content_type='application/pdf')
        filename = f"activities_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except json.JSONDecodeError:
        messages.error(request, 'Invalid activity IDs format.')
        return redirect('activities:activity_list')
    except Exception as e:
        messages.error(request, f'Error generating PDF report: {str(e)}')
        return redirect('activities:activity_list')
