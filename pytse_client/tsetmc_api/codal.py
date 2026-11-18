"""Company introduction (معرفی) from codal.

tse_settings constant and the page that calls it:

- TSE_TICKER_INTRODUCTION_URL, Codal/GetCodalPublisherBySymbol/{symbol}:
  instInfo, tab "معرفی". It takes the symbol (e.g. فولاد, URL encoded), not
  the insCode, and answers HTTP 500 for some funds.
"""

from dataclasses import dataclass
from typing import Any, Optional

import requests
from pytse_client import tse_settings
from pytse_client.tsetmc_api._convert import number_text_to_int
from pytse_client.utils.request_session import get_json


@dataclass(frozen=True, slots=True)
class CodalPublisher:
    """Company introduction (key codalPublisher), tab "معرفی". The en*
    fields and a few others are null in every answer seen."""

    # financialYear: سال مالی, end of the fiscal year as "MM/DD", e.g.
    # "12/29"
    financial_year: Optional[str]
    # id: codal id of the publisher
    id: Optional[int] = None
    # symbol: نماد
    symbol: Optional[str] = None
    # displaySymbol: symbol as shown
    display_symbol: Optional[str] = None
    # name: نام شرکت
    name: Optional[str] = None
    # isic: ISIC code of the activity
    isic: Optional[str] = None
    # reportingType: codal reporting type code, e.g. "1000000"
    reporting_type: Optional[str] = None
    # executiveManager: مدیر عامل
    executive_manager: Optional[str] = None
    # financialManager: مدیر مالی
    financial_manager: Optional[str] = None
    # address: نشانی
    address: Optional[str] = None
    # officeAddress: نشانی دفتر مرکزی
    office_address: Optional[str] = None
    # shareOfficeAddress: نشانی امور سهام
    share_office_address: Optional[str] = None
    # telNo: تلفن
    tel_no: Optional[str] = None
    # faxNo: فکس
    fax_no: Optional[str] = None
    # website: وب سایت
    website: Optional[str] = None
    # email: ایمیل
    email: Optional[str] = None
    # activitySubject: موضوع فعالیت
    activity_subject: Optional[str] = None
    # state: codal state code, e.g. "0"
    state: Optional[str] = None
    # stateName: name of the state
    state_name: Optional[str] = None
    # companyType: codal company type code, e.g. "0"
    company_type: Optional[str] = None
    # companyType1: second company type code
    company_type1: Optional[str] = None
    # inspector: بازرس
    inspector: Optional[str] = None
    # auditorName: حسابرس
    auditor_name: Optional[str] = None
    # inspListedCapitalector: (sic) null in every answer seen
    insp_listed_capitalector: Optional[str] = None
    # listedCapital: سرمایه ثبت شده, million rial, sent as text
    listed_capital: Optional[int] = None
    # companyId: codal company id
    company_id: Optional[str] = None
    # nationalCode: شناسه ملی
    national_code: Optional[str] = None
    # managementGroup: گروه مدیریت
    management_group: Optional[str] = None
    # enManagementGroup: English management group
    en_management_group: Optional[str] = None
    # enName: English name
    en_name: Optional[str] = None
    # enDisplayedSymbol: English symbol
    en_displayed_symbol: Optional[str] = None
    # enActivitySubject: English activity subject
    en_activity_subject: Optional[str] = None
    # enAddress: English address
    en_address: Optional[str] = None
    # enOfficeAddress: English office address
    en_office_address: Optional[str] = None
    # enShareOfficeAddress: English share office address
    en_share_office_address: Optional[str] = None
    # enExecutiveManager: English executive manager
    en_executive_manager: Optional[str] = None
    # enFinancialManager: English financial manager
    en_financial_manager: Optional[str] = None
    # enInspector: English inspector
    en_inspector: Optional[str] = None


def parse_codal_publisher(data: Any) -> Optional[CodalPublisher]:
    """Parse the JSON of Codal/GetCodalPublisherBySymbol/{symbol}, None
    when the API sends no publisher."""
    publisher = data.get("codalPublisher")
    if not publisher:
        return None
    return CodalPublisher(
        financial_year=publisher["financialYear"],
        id=publisher.get("id"),
        symbol=publisher.get("symbol"),
        display_symbol=publisher.get("displaySymbol"),
        name=publisher.get("name"),
        isic=publisher.get("isic"),
        reporting_type=publisher.get("reportingType"),
        executive_manager=publisher.get("executiveManager"),
        financial_manager=publisher.get("financialManager"),
        address=publisher.get("address"),
        office_address=publisher.get("officeAddress"),
        share_office_address=publisher.get("shareOfficeAddress"),
        tel_no=publisher.get("telNo"),
        fax_no=publisher.get("faxNo"),
        website=publisher.get("website"),
        email=publisher.get("email"),
        activity_subject=publisher.get("activitySubject"),
        state=publisher.get("state"),
        state_name=publisher.get("stateName"),
        company_type=publisher.get("companyType"),
        company_type1=publisher.get("companyType1"),
        inspector=publisher.get("inspector"),
        auditor_name=publisher.get("auditorName"),
        insp_listed_capitalector=publisher.get("inspListedCapitalector"),
        listed_capital=number_text_to_int(publisher.get("listedCapital")),
        company_id=publisher.get("companyId"),
        national_code=publisher.get("nationalCode"),
        management_group=publisher.get("managementGroup"),
        en_management_group=publisher.get("enManagementGroup"),
        en_name=publisher.get("enName"),
        en_displayed_symbol=publisher.get("enDisplayedSymbol"),
        en_activity_subject=publisher.get("enActivitySubject"),
        en_address=publisher.get("enAddress"),
        en_office_address=publisher.get("enOfficeAddress"),
        en_share_office_address=publisher.get("enShareOfficeAddress"),
        en_executive_manager=publisher.get("enExecutiveManager"),
        en_financial_manager=publisher.get("enFinancialManager"),
        en_inspector=publisher.get("enInspector"),
    )


def fetch_codal_publisher(
    symbol: str,
    session: Optional[requests.Session] = None,
    timeout: float = 10,
) -> Optional[CodalPublisher]:
    """GET and parse TSE_TICKER_INTRODUCTION_URL of a symbol (e.g. فولاد).

    Raises a requests.RequestException for symbols the API has no
    introduction of (it answers HTTP 500 for some funds).
    """
    return parse_codal_publisher(
        get_json(
            tse_settings.TSE_TICKER_INTRODUCTION_URL.format(symbol),
            session=session,
            timeout=timeout,
        )
    )
