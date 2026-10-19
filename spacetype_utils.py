# spacetype_utils.py

"""
Utilities for mapping SpaceTypes to APP/APT categories in building-modeling scripts.

- SPACETYPE_DICTIONARY: maps space type names to "APP" or "APT"
- get_space_type_label(space): given an OpenStudio Space object, returns "APP", "APT", or None.
- get_space_type_label_by_name(name): returns "APP", "APT", or None when given the space type name as a string.
"""

SPACETYPE_DICTIONARY = {
    "ActiveStorage": "APP",
    "ActiveStorageHospitalOrHealthcare": "APP",
    "AirOrTrainOrBusBaggageArea": "APT",
    "AirportConcourse": "APT",
    "AtriumEachAdditionalFloor": "APT",
    "AtriumFirstThreeFloors": "APT",
    "AudienceOrSeatingAreaPenitentiary": "APP",
    "AudienceOrSeatingAreaExerciseCenter": "APP",
    "AudienceOrSeatingAreaGymnasium": "APP",
    "AudienceOrSeatingAreaSportsArena": "APP",
    "AudienceOrSeatingAreaConventionCenter": "APP",
    "AudienceOrSeatingAreaMotionPictureTheatre": "APP",
    "AudienceOrSeatingAreaPerformingArtsTheatre": "APP",
    "AudienceOrSeatingAreaReligious": "APP",
    "AudienceOrSeatingAreaPoliceOrFireStations": "APP",
    "AudienceOrSeatingAreaCourtHouse": "APP",
    "AudienceOrSeatingAreaAuditorium": "APP",
    "BankCustomerArea": "APP",
    "BankingActivityAreaOffice": "APP",
    "BarberAndBeautyParlor": "APP",
    "CardFileAndCataloguingLibrary": "APP",
    "ClassroomOrLectureOrTrainingPenitentiary": "APP",
    "ClassroomOrLectureOrTraining": "APP",
    "ConfinementCellsPenitentiary": "APP",
    "ConfinementCellsCourtHouse": "APP",
    "ConferenceMeetingOrMultipurpose": "APP",
    "CorridorOrTransition": "APT",
    "CorridorOrTransitionManufacturingFacility": "APT",
    "CorridorsWithPatientWaitingExamHospitalOrHealthcare": "APP",
    "CourtSportsAreaSportsArena": "APT",
    "CourtroomCourtHouse": "APP",
    "DepartmentStoreSalesAreaRetail": "APP",
    "DetailedManufacturingFacility": "APP",
    "DiningArea": "APP",
    "DiningAreaHotel": "APP",
    "DiningAreaFamilyDining": "APP",
    "DiningAreaLoungeOrLeisureDining": "APP",
    "DiningAreaMotel": "APP",
    "DiningAreaTransportation": "APP",
    "DiningAreaPenitentiary": "APP",
    "DiningAreaCivilServices": "APP",
    "DormitoryBedroom": "APP",
    "DormitoryStudyHall": "APP",
    "DressingOrLockerOrFittingRoomGymnasium": "APT",
    "DressingOrLockerOrFittingRoomCourtHouse": "APT",
    "DressingOrLockerOrFittingRoomPerformingArtsTheatre": "APT",
    "DressingOrLockerOrFittingRoomAuditorium": "APT",
    "DressingOrLockerOrFittingRoomExerciseCenter": "APT",
    "ElectricalOrMechanical": "APT",
    "ElevatorLobbies": "APT",
    "EmergencyHospitalOrHealthcare": "APP",
    "EquipmentRoomManufacturingFacility": "APT",
    "ExamOrTreatmentHospitalOrHealthcare": "APP",
    "ExcerciseAreaExerciseCenter": "APP",
    "ExcerciseAreaGymnasium": "APP",
    "ExhibitSpaceConventionCenter": "APT",
    "FellowshipHallReligiousBuildings": "APP",
    "FineMaterialWarehouse": "APT",
    "FineMerchandiseSalesAreaRetail": "APT",
    "FireStationEngineRoomPoliceOrFireStation": "APT",
    "FoodPreparation": "APP",
    "GarageServiceOrRepairAutomotiveFacility": "APT",
    "GeneralHighBayManufacturingFacility": "APP",
    "GeneralLowBayManufacturingFacility": "APP",
    "GeneralExhibitionMuseum": "APP",
    "HospitalNurseryHospitalOrHealthcare": "APP",
    "HospitalOrMedicalSuppliesHospitalOrHealthcare": "APP",
    "HospitalOrRadiologyHospitalOrHealthcare": "APP",
    "HotelOrConferenceCenterConferenceOrMeeting": "APP",
    "InactiveStorage": "APT",
    "JudgesChambersCourtHouse": "APP",
    "LaboratoryOffice": "APP",
    "LaundryIroningAndSorting": "APP",
    "LaundryWashingHospitalOrHealthcare": "APP",
    "LibraryAudioVisualLibraryAudioVisual": "APP",
    "LivingQuartersDormitory": "APP",
    "LivingQuartersMotel": "APP",
    "LivingQuartersHotel": "APP",
    "Lobby": "APT",
    "LobbyReligiousBuildings": "APT",
    "LobbyMotionPictureTheatre": "APT",
    "LobbyAuditorium": "APT",
    "LobbyPerformingArtsTheatre": "APT",
    "LobbyPostOffice": "APT",
    "LobbyHotel": "APT",
    "LoungeOrRecreation": "APP",
    "MallConcourseSalesAreaRetail": "APT",
    "MassMerchandisingSalesAreaRetail": "APP",
    "MediumOrBulkyMaterialWarehouse": "APT",
    "MerchandisingSalesAreaRetail": "APP",
    "MuseumAndGalleryStorage": "APT",
    "NurseStationHospitalOrHealthcare": "APP",
    "OfficeEnclosed": "APP",
    "OfficeOpenPlan": "APP",
    "OfficeCommonActivityAreasInactiveStorage": "APP",
    "OperatingRoomHospitalOrHealthcare": "APP",
    "OtherTelevisedPlayingAreaSportsArena": "APT",
    "ParkingAreaAttendantOnlyParkingGarage": "APT",
    "ParkingAreaPedestrianParkingGarage": "APT",
    "PatientRoomHospitalOrHealthcare": "APP",
    "PersonalServicesSalesAreaRetail": "APP",
    "PharmacyHospitalOrHealthcare": "APP",
    "PhysicalTherapyHospitalOrHealthcare": "APP",
    "PlayingAreaGymnasium": "APP",
    "Plenum": "APT",
    "PoliceStationLaboratoryPoliceOrFireStations": "APP",
    "PublicAndStaffLoungeHospitalOrHealthcare": "APP",
    "ReadingAreaLibrary": "APP",
    "ReceptionOrWaitingTransportation": "APT",
    "ReceptionOrWaitingMotel": "APT",
    "ReceptionOrWaitingHotel": "APT",
    "RecoveryHospitalOrHealthcare": "APP",
    "RestorationMuseum": "APP",
    "Restrooms": "APT",
    "RingSportsAreaSportsArena": "APT",
    "ServerRoom": "APT",
    "SleepingQuartersPoliceOrFireStation": "APP",
    "SortingAreaPostOffice": "APT",
    "SpecialtyStoreSalesAreaRetail": "APP",
    "StacksLibrary": "APP",
    "StairsInactive": "APT",
    "Stairway": "APT",
    "SupermarketSalesAreaRetail": "APP",
    "TerminalTicketCounterTransportation": "APT",
    "WorkshopWorkshop": "APP",
    "WorshipPulpitChoirReligious": "APP"
}

def get_space_type_label(space, dictionary=SPACETYPE_DICTIONARY):
    """
    Takes an OpenStudio Space object and returns "APP", "APT", or None.
    """
    if not hasattr(space, 'spaceType') or not callable(getattr(space, 'spaceType', None)):
        # Not an OpenStudio Space object
        return None
    if not space.spaceType().is_initialized():
        return None
    space_type = space.spaceType().get()
    # Try OpenStudio >= 3.1 style, or fallback to the legacy
    if hasattr(space_type, 'nameString'):
        space_type_name = space_type.nameString()
    else:
        space_type_name = space_type.name().get() if space_type.name().is_initialized() else None
    if not space_type_name:
        return None
    return dictionary.get(space_type_name, None)

def get_space_type_label_by_name(space_type_name, dictionary=SPACETYPE_DICTIONARY):
    """
    Takes a space type name (str) and returns "APP", "APT", or None.
    """
    return dictionary.get(space_type_name, None)
