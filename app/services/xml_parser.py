import logging

from lxml import etree

from app.models.schemas import (
    AddressInfo,
    DentistInfo,
    FileInfo,
    OrderInfo,
    OriginatorInfo,
    PatientInfo,
    RestorationInfo,
)


logger = logging.getLogger("ids.xml_parser")


class IDSParseError(Exception):
    pass


def parse_ids_xml(xml_bytes: bytes) -> dict:
    """Parse an IDS XML document and return structured data."""
    logger.debug("Parsing IDS XML (%d bytes)", len(xml_bytes))

    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as e:
        logger.error("XML syntax error: %s", e)
        raise IDSParseError(f"Invalid XML: {e}")

    if root.tag != "IDS":
        logger.error("Invalid root element: <%s>", root.tag)
        raise IDSParseError(f"Root element must be <IDS>, got <{root.tag}>")

    ids_version = root.get("IDSVersion")
    ids_uuid = root.get("IDSUUID")
    if not ids_version or not ids_uuid:
        raise IDSParseError("IDS root must have IDSVersion and IDSUUID attributes")

    logger.info("Parsed IDS: version=%s, uuid=%s", ids_version, ids_uuid)

    result = {
        "ids_version": ids_version,
        "ids_uuid": ids_uuid,
    }

    # Parse Submission
    submission = root.find("Submission")
    if submission is not None:
        result["submission"] = _parse_submission(submission)

    # Parse Notification (for non-submission documents)
    notification = root.find("Notification")
    if notification is not None:
        result["notification"] = {
            "uuid": notification.get("UUID", ""),
            "type": notification.get("Type", ""),
        }
        logger.info("Parsed Notification: type=%s", notification.get("Type"))

    return result


def _parse_submission(elem) -> dict:
    sub = {
        "uuid": elem.get("UUID", ""),
        "date_submitted": elem.get("DateUTCSubmitted", ""),
        "date_received": elem.get("DateUTCReceived", ""),
    }
    logger.info("Parsing Submission: uuid=%s", sub["uuid"])

    originator = elem.find("Originator")
    if originator is not None:
        sub["originator"] = _parse_originator(originator)

    catalogs = elem.find("Catalogs")
    if catalogs is not None:
        sub["patients"] = _parse_patients(catalogs.find("PatientCatalog"))
        sub["dentists"] = _parse_dentists(catalogs.find("DentistCatalog"))
        sub["orders"] = _parse_orders(catalogs.find("OrderCatalog"))
        sub["files"] = _parse_files(catalogs.find("FileCatalog"))
        logger.info(
            "Catalogs: patients=%d, dentists=%d, orders=%d, files=%d",
            len(sub["patients"]), len(sub["dentists"]), len(sub["orders"]), len(sub["files"]),
        )

    return sub


def _parse_originator(elem) -> dict:
    info = OriginatorInfo(
        uuid=elem.get("UUID", ""),
        name=elem.get("Name", ""),
        business_type=elem.get("BusinessType"),
    )
    address = None
    addr_elem = elem.find("Address")
    if addr_elem is not None:
        address = AddressInfo(
            street1=addr_elem.get("Street1"),
            street2=addr_elem.get("Street2"),
            city=addr_elem.get("City"),
            state=addr_elem.get("State"),
            postal_code=addr_elem.get("PostalCode"),
            country=addr_elem.get("Country"),
        )
    return {"info": info, "address": address}


def _parse_patients(catalog) -> list[PatientInfo]:
    if catalog is None:
        return []
    result = []
    for p in catalog.findall("Patient"):
        result.append(PatientInfo(
            uuid=p.get("UUID", ""),
            first_name=p.get("FirstName"),
            last_name=p.get("LastName"),
            date_of_birth=p.get("DateOfBirth"),
            gender=p.get("Gender"),
        ))
    return result


def _parse_dentists(catalog) -> list[DentistInfo]:
    if catalog is None:
        return []
    result = []
    for d in catalog.findall("Dentist"):
        result.append(DentistInfo(
            uuid=d.get("UUID", ""),
            first_name=d.get("FirstName"),
            last_name=d.get("LastName"),
            license_number=d.get("LicenseNumber"),
        ))
    return result


def _parse_orders(catalog) -> list[OrderInfo]:
    if catalog is None:
        return []
    result = []
    for o in catalog.findall("Order"):
        restorations = []
        for r in o.findall("Restoration"):
            restorations.append(RestorationInfo(
                uuid=r.get("UUID", ""),
                tooth_number=r.get("ToothNumber"),
                type=r.get("Type"),
                material=r.get("Material"),
                shade=r.get("Shade"),
            ))
        result.append(OrderInfo(
            uuid=o.get("UUID", ""),
            patient_uuid=o.get("PatientUUID"),
            dentist_uuid=o.get("DentistUUID"),
            priority=o.get("Priority"),
            date_created=o.get("DateUTCCreated"),
            restorations=restorations,
        ))
    return result


def _parse_files(catalog) -> list[FileInfo]:
    if catalog is None:
        return []
    result = []
    for f in catalog.findall("IDSFile"):
        result.append(FileInfo(
            uuid=f.get("UUID", ""),
            file_name=f.get("FileName", ""),
            file_type=f.get("FileType"),
            file_size=f.get("FileSize"),
            description=f.get("Description"),
        ))
    return result
