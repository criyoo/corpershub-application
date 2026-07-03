from django.urls import path

from apps.interests.views import (
    CompanyExpressInterestAPIView,
    CompanySavedInterestsAPIView,
    ExpressInterestAPIView,
    InterestedCorpersAPIView,
    MyInterestsAPIView,
    CorperInterestedCompaniesAPIView,
)

urlpatterns = [
    path("companies/<uuid:company_id>/express/", ExpressInterestAPIView.as_view(), name="express-interest"),
    path(
        "corpers/<uuid:corper_id>/express/",
        CompanyExpressInterestAPIView.as_view(),
        name="company-express-interest",
    ),
    path("mine/", MyInterestsAPIView.as_view(), name="my-interests"),
    path("companies/received/", CorperInterestedCompaniesAPIView.as_view(), name="corper-received-company-interests"),
    path("saved/", CompanySavedInterestsAPIView.as_view(), name="saved-interests"),
    path("received/", InterestedCorpersAPIView.as_view(), name="received-interests"),
]
