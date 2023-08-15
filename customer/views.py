from django.shortcuts import render, redirect, reverse
from . import forms, models
from django.db.models import Sum
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.conf import settings
from datetime import date, timedelta
from django.db.models import Q
from django.core.mail import send_mail
from insurance import models as CMODEL
from insurance import forms as CFORM
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError

from django.http import HttpResponse, JsonResponse
from .models import Customer
import json
from django.contrib.auth import authenticate, login, get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from fcm_django.models import FCMDevice


def customerclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request, 'customer/customerclick.html')


def customer_signup_view(request):
    userForm = forms.CustomerUserForm()
    customerForm = forms.CustomerForm()
    mydict = {'userForm': userForm, 'customerForm': customerForm}
    if request.method == 'POST':
        userForm = forms.CustomerUserForm(request.POST)
        customerForm = forms.CustomerForm(request.POST, request.FILES)
        if userForm.is_valid() and customerForm.is_valid():
            user = userForm.save()
            user.set_password(user.password)
            user.save()
            customer = customerForm.save(commit=False)
            customer.user = user
            customer.save()
            my_customer_group = Group.objects.get_or_create(name='CUSTOMER')
            my_customer_group[0].user_set.add(user)
        return HttpResponseRedirect('customerlogin')
    return render(request, 'customer/customersignup.html', context=mydict)


def is_customer(user):
    return user.groups.filter(name='CUSTOMER').exists()


@login_required(login_url='customerlogin')
def customer_dashboard_view(request):
    dict = {
        'customer': models.Customer.objects.get(user_id=request.user.id),
        'available_policy': CMODEL.Policy.objects.all().count(),
        'applied_policy': CMODEL.PolicyRecord.objects.all().filter(customer=models.Customer.objects.get(user_id=request.user.id)).count(),
        'total_category': CMODEL.Category.objects.all().count(),
        'total_question': CMODEL.Question.objects.all().filter(customer=models.Customer.objects.get(user_id=request.user.id)).count(),

    }
    return render(request, 'customer/customer_dashboard.html', context=dict)


def apply_policy_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    policies = CMODEL.Policy.objects.all()
    return render(request, 'customer/apply_policy.html', {'policies': policies, 'customer': customer})


def apply_view(request, pk):
    customer = models.Customer.objects.get(user_id=request.user.id)
    policy = CMODEL.Policy.objects.get(id=pk)
    policyrecord = CMODEL.PolicyRecord()
    policyrecord.Policy = policy
    policyrecord.customer = customer
    policyrecord.save()
    return redirect('history')


def history_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    policies = CMODEL.PolicyRecord.objects.all().filter(customer=customer)
    return render(request, 'customer/history.html', {'policies': policies, 'customer': customer})


def ask_question_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    questionForm = CFORM.QuestionForm()

    if request.method == 'POST':
        questionForm = CFORM.QuestionForm(request.POST)
        if questionForm.is_valid():

            question = questionForm.save(commit=False)
            question.customer = customer
            question.save()
            return redirect('question-history')
    return render(request, 'customer/ask_question.html', {'questionForm': questionForm, 'customer': customer})


def question_history_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    questions = CMODEL.Question.objects.all().filter(customer=customer)
    return render(request, 'customer/question_history.html', {'questions': questions, 'customer': customer})


@csrf_exempt
def create_new_customer(request):
    if request.method == 'POST':
        body = json.loads(request.body.decode('utf-8'))
        address = body.get('address')
        mobile = body.get('mobile')
        user = body.get('user')
        firstName = user['first_name']
        lastName = user['last_name']
        userName = user['username']
        email = user['email']
        password = user['password']
        try:
            new_user = User(first_name=firstName, last_name=lastName,
                            username=userName, email=email, password=password)
            new_user.set_password(new_user.password)
            new_user.save()
        except IntegrityError:
            return JsonResponse({'success': False, 'error': 'Username already exists'})

        fcm_device = FCMDevice()
        fcm_device.registration_id = body.get('fcm_token')
        fcm_device.type = body.get('device_type')
        fcm_device.user = new_user
        fcm_device.save()

        new_customer = Customer(user=new_user, mobile=mobile, address=address)
        new_customer.save()
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method'})


@csrf_exempt
def login_api(request):
    body = json.loads(request.body.decode('utf-8'))
    email = body.get('email')
    password = body.get('password')

    User = get_user_model()
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        user = None

    if user is not None and user.check_password(password):
        # password correct
        user = authenticate(request, username=user.username, password=password)
        if user is not None:
            # authentication successful
            user_id = user.id
            customer_id = Customer.objects.values_list(
                'id', flat=True).get(user_id=user_id)
            return JsonResponse({'success': True, 'customer_id': customer_id})
    else:
        return JsonResponse({'success': False})
