from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def dashboard(request):
    return render(request, 'core/dashboard.html', {'role_label': request.user.get_role_display()})

# Create your views here.
