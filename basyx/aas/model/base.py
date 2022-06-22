# Copyright (c) 2020 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
This module implements the basic structures of the AAS meta-model, including the abstract classes and enums needed for
the higher level classes to inherit from.
"""

import abc
import inspect
import itertools
from enum import Enum, unique
from typing import List, Optional, Set, TypeVar, MutableSet, Generic, Iterable, Dict, Iterator, Union, overload, \
    MutableSequence, Type, Any, TYPE_CHECKING, Tuple
import re

from . import datatypes
from ..backend import backends

if TYPE_CHECKING:
    from . import provider

DataTypeDef = Type[datatypes.AnyXSDType]
ValueDataType = datatypes.AnyXSDType  # any xsd atomic type (from .datatypes)
BlobType = bytes
ContentType = str  # any mimetype as in RFC2046
PathType = str
QualifierType = str
# A dict of language-Identifier (according to ISO 639-1 and ISO 3166-1) and string in this language.
# The meaning of the string in each language is the same.
# << Data Type >> Example ["en-US", "germany"]
LangStringSet = Dict[str, str]


@unique
class IdentifierType(Enum):
    """
    Enumeration of different types of :class:`Identifiers <.Identifier>` for global identification

    :cvar IRDI: IRDI (International Registration Data Identifier) according to ISO29002-5 as an Identifier scheme for
                properties and classifications.
    :cvar IRI: IRI according to Rfc 3987. Every URI is an IRI
    :cvar CUSTOM: Custom identifiers like GUIDs (globally unique Identifiers)
    """

    IRDI = 0
    IRI = 1
    CUSTOM = 2


@unique
class KeyElements(Enum):
    """
    Enumeration for denoting which kind of entity is referenced. They can be categorized in ReferableElements,
    IdentifiableElements and other KeyElements

    **IdentifiableElements starting from 0**

    :cvar ASSET_ADMINISTRATION_SHELL: :class:`~aas.model.aas.AssetAdministrationShell`
    :cvar CONCEPT_DESCRIPTION: :class:`~aas.model.concept.ConceptDescription`
    :cvar SUBMODEL: :class:`~aas.model.submodel.Submodel`

    **ReferableElements starting from 1000**

    *Note:* DataElement is abstract, i. e. if a key uses :attr:`~.KeyElements.DATA_ELEMENT` the reference may be
    :class:`~aas.model.submodel.Property`, :class:`~aas.model.submodel.File` etc.

    *Note:* SubmodelElement is abstract, i.e. if a key uses :attr:`~.KeyElements.SUBMODEL_ELEMENT`
    the reference may be a :class:`~aas.model.submodel.Property`, a
    :class:`~aas.model.submodel.SubmodelElementCollection`, an :class:`~aas.model.submodel.Operation` etc.

    :cvar ACCESS_PERMISSION_RULE: access permission rule
    :cvar ANNOTATED_RELATIONSHIP_ELEMENT: :class:`~aas.model.submodel.AnnotatedRelationshipElement`
    :cvar BASIC_EVENT_ELEMENT: :class:`~aas.model.submodel.BasicEventElement`
    :cvar BLOB: :class:`~aas.model.submodel.Blob`
    :cvar CAPABILITY: :class:`~aas.model.submodel.Capability`
    :cvar CONCEPT_DICTIONARY: :class:`~aas.model.concept.ConceptDictionary`
    :cvar DATA_ELEMENT: :class:`~aas.model.submodel.DataElement`
    :cvar ENTITY: :class:`~aas.model.submodel.Entity`
    :cvar EVENT_ELEMENT: :class:`~aas.model.submodel.EventElement`, Note: EventElement is abstract
    :cvar FILE: :class:`~aas.model.submodel.File`
    :cvar MULTI_LANGUAGE_PROPERTY: :class:`~aas.model.submodel.MultiLanguageProperty` property with a value that can be
                                   provided in multiple languages
    :cvar OPERATION: :class:`~aas.model.submodel.Operation`
    :cvar PROPERTY: :class:`~aas.model.submodel.Property`
    :cvar RANGE: :class:`~aas.model.submodel.Range` with min and max
    :cvar REFERENCE_ELEMENT: :class:`~aas.model.submodel.ReferenceElement`
    :cvar RELATIONSHIP_ELEMENT: :class:`~aas.model.submodel.RelationshipElement`
    :cvar SUBMODEL_ELEMENT: :class:`~aas.model.submodel.SubmodelElement`
    :cvar SUBMODEL_ELEMENT_COLLECTION: :class:`~aas.model.submodel.SubmodelElementCollection`

    **KeyElements starting from 2000**

    :cvar GLOBAL_REFERENCE: reference to an element not belonging to an asset administration shell
    :cvar FRAGMENT_REFERENCE: unique reference to an element within a file. The file itself is assumed to be part of an
                              asset administration shell.
    """

    # IdentifiableElements starting from 0
    # keep _ASSET = 0 as a protected enum member here, so 0 isn't reused in the enum by a future identifiable
    _ASSET = 0
    ASSET_ADMINISTRATION_SHELL = 1
    CONCEPT_DESCRIPTION = 2
    SUBMODEL = 3

    # ReferableElements starting from 1000
    ACCESS_PERMISSION_RULE = 1000
    ANNOTATED_RELATIONSHIP_ELEMENT = 1001
    BASIC_EVENT_ELEMENT = 1002
    BLOB = 1003
    CAPABILITY = 1004
    CONCEPT_DICTIONARY = 1005
    DATA_ELEMENT = 1006
    ENTITY = 1007
    EVENT_ELEMENT = 1008
    FILE = 1009
    MULTI_LANGUAGE_PROPERTY = 1010
    OPERATION = 1011
    PROPERTY = 1012
    RANGE = 1013
    REFERENCE_ELEMENT = 1014
    RELATIONSHIP_ELEMENT = 1015
    SUBMODEL_ELEMENT = 1016
    SUBMODEL_ELEMENT_COLLECTION = 1017
    # keep _VIEW = 1018 as a protected enum member here, so 1018 isn't reused in the enum by a future referable
    _VIEW = 1018

    # KeyElements starting from 2000
    GLOBAL_REFERENCE = 2000
    FRAGMENT_REFERENCE = 2001


@unique
class KeyType(Enum):
    """
    Enumeration for denoting the type of the key value.

    :cvar IRDI: IRDI (International Registration Data Identifier) according to ISO29002-5 as an Identifier scheme for
                properties and classifications.
    :cvar IRI: IRI according to Rfc 3987. Every URI is an IRI
    :cvar CUSTOM: Custom identifiers like GUIDs (globally unique Identifiers)
    :cvar IDSHORT: id_short of a referable element
    :cvar FRAGMENT_ID: identifier of a fragment within a file
    """

    IRDI = 0
    IRI = 1
    CUSTOM = 2
    IDSHORT = 3
    FRAGMENT_ID = 4

    @property
    def is_local_key_type(self) -> bool:
        return self in (KeyType.IDSHORT, KeyType.FRAGMENT_ID)


@unique
class EntityType(Enum):
    """
    Enumeration for denoting whether an entity is a self-managed or a co-managed entity

    :cvar CO_MANAGED_ENTITY: For co-managed entities there is no separate
                             :class:`AAS <aas.model.aas.AssetAdministrationShell>`. Co-managed entities need to be part
                             of a self-managed entity
    :cvar SELF_MANAGED_ENTITY: Self-managed entities have their own
                               :class:`AAS <aas.model.aas.AssetAdministrationShell>`, but can be part of the bill of
                               material of a composite self-managed entity.
    """

    CO_MANAGED_ENTITY = 0
    SELF_MANAGED_ENTITY = 1


@unique
class ModelingKind(Enum):
    """
    Enumeration for denoting whether an element is a type or an instance.
    *Note:* An :attr:`~.ModelingKind.INSTANCE` becomes an individual entity of a template, for example a device model,
    by defining specific property values.

    *Note:* In an object oriented view, an instance denotes an object of a template (class).

    :cvar TEMPLATE: Software element which specifies the common attributes shared by all instances of the template
    :cvar INSTANCE: concrete, clearly identifiable component of a certain template.
        *Note:*  It becomes an individual entity of a template, for example a device model, by defining
        specific property values.
        *Note:* In an object oriented view, an instance denotes an object of a template (class).
    """

    TEMPLATE = 0
    INSTANCE = 1


@unique
class AssetKind(Enum):
    """
    Enumeration for denoting whether an element is a type or an instance.
    *Note:* :attr:`~.AssetKind.INSTANCE` becomes an individual entity of a type, for example a device, by defining
    specific property values.

    *Note:* In an object oriented view, an instance denotes an object of a class (of a type)

    :cvar TYPE: hardware or software element which specifies the common attributes shared by all instances of the type
    :cvar INSTANCE: concrete, clearly identifiable component of a certain type,
                    *Note:* It becomes an individual entity of a type, for example a device, by defining specific
                    property values.
                    *Note:* In an object oriented view, an instance denotes an object of a class (of a type)
    """

    TYPE = 0
    INSTANCE = 1


LOCAL_KEY_TYPES: Set[KeyType] = {
    KeyType.IDSHORT,
    KeyType.FRAGMENT_ID
}


class Key:
    """
    A key is a reference to an element by its id.

    *Constraint AASd-080:* A Key with :attr:`~.type` == :attr:`~.KeyElements.GLOBAL_REFERENCE` must not have an
    :attr:`~.id_type` of LocalKeyType: (:attr:`~.KeyElements.IDSHORT`, :attr:`~.KeyElements.FRAGMENT_ID`)

    *Constraint AASd-081:* A Key with :attr:`~.type` == :attr:`~.KeyElements.ASSET_ADMINISTRATION_SHELL` must not have
    an :attr:`~.id_type` of LocalKeyType: (:attr:`~.KeyElements.IDSHORT`, :attr:`~.KeyElements.FRAGMENT_ID`)

    :ivar type_: Denote which kind of entity is referenced. In case type = :attr:`~.KeyElements.GLOBAL_REFERENCE` then
                the element is a global unique id. In all other cases the key references a model element of the same or
                of another AAS. The name of the model element is explicitly listed.
    :ivar value: The key value, for example an IRDI if the idType = :attr:`~.KeyType.IRDI`
    :ivar id_type: Type of the key value. In case type =
                   :attr:`~.KeyElements.GLOBAL_REFERENCE` idType shall not be IdShort.
    """

    def __init__(self,
                 type_: KeyElements,
                 value: str,
                 id_type: KeyType):
        """
        TODO: Add instruction what to do after construction
        """
        self.type: KeyElements
        if value == "":
            raise ValueError("value is not allowed to be an empty string")
        self.value: str
        self.id_type: KeyType
        super().__setattr__('type', type_)
        super().__setattr__('value', value)
        super().__setattr__('id_type', id_type)
        if self.type is KeyElements.GLOBAL_REFERENCE and self.id_type in LOCAL_KEY_TYPES:
            raise AASConstraintViolation(
                80,
                "A Key with Key.type==GLOBAL_REFERENCE must not have an id_type of LocalKeyType: (IDSHORT, FRAGMENT_ID)"
            )
        if self.type is KeyElements.ASSET_ADMINISTRATION_SHELL and self.id_type in LOCAL_KEY_TYPES:
            raise AASConstraintViolation(
                81,
                "A Key with Key.type==ASSET_ADMINISTRATION_SHELL must not have an id_type of LocalKeyType: " +
                ", ".join([key_type.name for key_type in LOCAL_KEY_TYPES])
            )

    def __setattr__(self, key, value):
        """Prevent modification of attributes."""
        raise AttributeError('Reference is immutable')

    def __repr__(self) -> str:
        return "Key(id_type={}, value={})".format(self.id_type.name, self.value)

    def __str__(self) -> str:
        return "{}={}".format(self.id_type.name, self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Key):
            return NotImplemented
        return (self.id_type is other.id_type
                and self.value == other.value
                and self.type == other.type)

    def __hash__(self):
        return hash((self.id_type, self.value, self.type))

    def get_identifier(self) -> Optional["Identifier"]:
        """
        Get an :class:`~.Identifier` object corresponding to this key, if it is a global key.

        :return: None if this is no global key, otherwise a corresponding :class:`~.Identifier` object
        """
        if self.id_type.is_local_key_type:
            return None
        return Identifier(self.value, IdentifierType(self.id_type.value))

    @staticmethod
    def from_referable(referable: "Referable") -> "Key":
        """
        Construct a key for a given :class:`~.Referable` (or :class:`~.Identifiable`) object

        :param referable: :class:`~.Referable` or :class:`~.Identifiable` object
        :returns: :class:`~.Key`
        """
        # Get the `type` by finding the first class from the base classes list (via inspect.getmro), that is contained
        # in KEY_ELEMENTS_CLASSES
        from . import KEY_ELEMENTS_CLASSES
        try:
            key_type = next(iter(KEY_ELEMENTS_CLASSES[t]
                                 for t in inspect.getmro(type(referable))
                                 if t in KEY_ELEMENTS_CLASSES))
        except StopIteration:
            key_type = KeyElements.PROPERTY

        if isinstance(referable, Identifiable):
            return Key(key_type, referable.identification.id,
                       KeyType(referable.identification.id_type.value))
        else:
            return Key(key_type, referable.id_short, KeyType.IDSHORT)


class AdministrativeInformation:
    """
    Administrative meta-information for an element like version information.

    *Constraint AASd-005:* A revision requires a version. This means, if there is no version there is no revision
    either.

    :ivar version: Version of the element.
    :ivar revision: Revision of the element.
    """

    def __init__(self,
                 version: Optional[str] = None,
                 revision: Optional[str] = None):
        """
        Initializer of AdministrativeInformation

        :raises ValueError: If version is None and revision is not None

        TODO: Add instruction what to do after construction
        """
        self._version: Optional[str]
        self.version = version
        self._revision: Optional[str]
        self.revision = revision

    def _get_version(self):
        return self._version

    def _set_version(self, version: str):
        if version == "":
            raise ValueError("version is not allowed to be an empty string")
        self._version = version

    version = property(_get_version, _set_version)

    def _get_revision(self):
        return self._revision

    def _set_revision(self, revision: str):
        if revision == "":
            raise ValueError("revision is not allowed to be an empty string")
        if self.version is None and revision:
            raise ValueError("A revision requires a version. This means, if there is no version there is no revision "
                             "neither. Please set version first.")
        self._revision = revision

    revision = property(_get_revision, _set_revision)

    def __eq__(self, other) -> bool:
        if not isinstance(other, AdministrativeInformation):
            return NotImplemented
        return self.version == other.version and self._revision == other._revision

    def __repr__(self) -> str:
        return "AdministrativeInformation(version={}, revision={})".format(self.version, self.revision)


class Identifier:
    """
    Used to uniquely identify an entity by using an identifier.

    :ivar ~.id: Identifier of the element. Its type is defined in id_type. (*Initialized as:* `id_`)
    :ivar id_type: Type of the Identifier, e.g. URI, IRDI etc. The supported Identifier types are defined in
                   the :class:`~.IdentifierType` enumeration.
    """

    def __init__(self,
                 id_: str,
                 id_type: IdentifierType):
        """
        TODO: Add instruction what to do after construction
        """
        self.id: str
        self.id_type: IdentifierType
        if id_ == "":
            raise ValueError("id is not allowed to be an empty string")
        super().__setattr__('id', id_)
        super().__setattr__('id_type', id_type)

    def __setattr__(self, key, value):
        """Prevent modification of attributes."""
        raise AttributeError('Identifier are immutable')

    def __hash__(self):
        return hash((self.id_type, self.id))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Identifier):
            return NotImplemented
        return self.id_type == other.id_type and self.id == other.id

    def __repr__(self) -> str:
        return "Identifier({}={})".format(self.id_type.name, self.id)


_NSO = TypeVar('_NSO', bound=Union["Referable", "Qualifier", "HasSemantics", "Extension"])


class Namespace(metaclass=abc.ABCMeta):
    """
    Abstract baseclass for all objects which form a Namespace to hold  objects and resolve them by their
    specific attribute.

    <<abstract>>

    :ivar namespace_element_sets: List of :class:`NamespaceSets <aas.model.base.NamespaceSet>`
    """
    @abc.abstractmethod
    def __init__(self) -> None:
        self.namespace_element_sets: List[NamespaceSet] = []

    def _get_object(self, object_type: type, attribute_name: str, attribute) -> _NSO:
        """
        Find an :class:`~._NSO` in this namespace by its attribute

        :raises KeyError: If no such :class:`~._NSO` can be found
        """
        for ns_set in self.namespace_element_sets:
            try:
                return ns_set.get_object_by_attribute(attribute_name, attribute)
            except KeyError:
                continue
        raise KeyError(f"{object_type.__name__} with {attribute_name} {attribute} not found in this namespace")

    def _add_object(self, attribute_name: str, obj: _NSO) -> None:
        """
        Add an :class:`~._NSO` to this namespace by its attribute

        :raises KeyError: If no such :class:`~._NSO` can be found
        """
        for ns_set in self.namespace_element_sets:
            if attribute_name not in ns_set.get_attribute_name_list():
                continue
            ns_set.add(obj)
            return
        raise ValueError(f"{obj!r} can't be added to this namespace")

    def _remove_object(self, object_type: type, attribute_name: str, attribute) -> None:
        """
        Remove an :class:`~.NSO` from this namespace by its attribute

        :raises KeyError: If no such :class:`~.NSO` can be found
        """
        for ns_set in self.namespace_element_sets:
            if attribute_name in ns_set.get_attribute_name_list():
                try:
                    ns_set.remove_by_id(attribute_name, attribute)
                    return
                except KeyError:
                    continue
        raise KeyError(f"{object_type.__name__} with {attribute_name} {attribute} not found in this namespace")


class HasExtension(Namespace, metaclass=abc.ABCMeta):
    """
    Abstract baseclass for all objects which form a Namespace to hold Extension objects and resolve them by their
    name.

    <<abstract>>

    *Constraint AASd-077:* The name of an extension within HasExtensions needs to be unique.

    TODO: This constraint is not yet implemented, a new Class for CustomSets should be implemented

    :ivar namespace_element_sets: List of :class:`NamespaceSets <aas.model.base.NamespaceSet>`
    :ivar extension: A :class:`~.NamespaceSet` of :class:`Extensions <.Extension>` of the element.
    :ivar _MEMBER_OBJ_TYPE: :class:`_NSO <aas.model.base.Namespace>`
    :ivar _ATTRIBUTE_NAME: Specific attribute name <aas.model.base.Namespace>`.
    """
    @abc.abstractmethod
    def __init__(self) -> None:
        self.namespace_element_sets: List[NamespaceSet] = []
        self.extension: NamespaceSet[Extension]

    def get_extension_by_name(self, name: str) -> "Extension":
        """
        Find an :class:`~.Extension` in this namespace by its name

        :raises KeyError: If no such :class:`~.Extension` can be found
        """
        return super()._get_object(HasExtension, "name", name)

    def add_extension(self, extension: "Extension") -> None:
        """
        Add a :class:`~.Extension` to this Namespace

        :param extension: The :class:`~.Extension` to add
        :raises KeyError: If a :class:`~.Extension` with the same name is already present in this namespace
        :raises ValueError: If the given :class:`~.Extension` already has a parent namespace
        """
        return super()._add_object("name", extension)

    def remove_extension_by_name(self, name: str) -> None:
        """
        Remove an :class:`~.Extension` from this namespace by its name

        :raises KeyError: If no such :class:`~.Extension` can be found
        """
        return super()._remove_object(HasExtension, "name", name)


class Referable(HasExtension, metaclass=abc.ABCMeta):
    """
    An element that is referable by its id_short. This id is not globally unique. This id is unique within
    the name space of the element.

    <<abstract>>

    *Constraint AASd-001:* In case of a referable element not being an identifiable element the
    idShort is mandatory and used for referring to the element in its name space.

    *Constraint AASd-002:* idShort shall only feature letters, digits, underscore ("_"); starting
    mandatory with a letter.

    *Constraint AASd-003:* idShort shall be matched case insensitive.

    *Constraint AASd-004:* Add parent in case of non identifiable elements.

    :ivar _id_short: Identifying string of the element within its name space
    :ivar ~.category: The category is a value that gives further meta information w.r.t. to the class of the element.
                      It affects the expected existence of attributes and the applicability of constraints.
    :ivar description: Description or comments on the element.
    :ivar parent: Reference (in form of a :class:`~.UniqueIdShortNamespace`) to the next referable parent element
        of the element.

    :ivar source: Source of the object, an URI, that defines where this object's data originates from.
                  This is used to specify where the Referable should be updated from and committed to.
                  Default is an empty string, making it use the source of its ancestor, if possible.
    """
    @abc.abstractmethod
    def __init__(self):
        super().__init__()
        self._id_short: str = "NotSet"
        self.display_name: Optional[LangStringSet] = set()
        self._category: Optional[str] = None
        self.description: Optional[LangStringSet] = set()
        # We use a Python reference to the parent Namespace instead of a Reference Object, as specified. This allows
        # simpler and faster navigation/checks and it has no effect in the serialized data formats anyway.
        self.parent: Optional[UniqueIdShortNamespace] = None
        self.source: str = ""

    def __repr__(self) -> str:
        reversed_path = []
        item = self  # type: Any
        while item is not None:
            if isinstance(item, Identifiable):
                reversed_path.append(str(item.identification))
                break
            elif isinstance(item, Referable):
                reversed_path.append(item.id_short)
                item = item.parent
            else:
                raise AttributeError('Referable must have an identifiable as root object and only parents that are '
                                     'referable')

        return "{}[{}]".format(self.__class__.__name__, " / ".join(reversed(reversed_path)))

    def _get_id_short(self):
        return self._id_short

    def _set_category(self, category: Optional[str]):
        """
        Check the input string

        Constraint AASd-100: An attribute with data type "string" is not allowed to be empty

        :param category: The category is a value that gives further meta information w.r.t. to the class of the element.
                         It affects the expected existence of attributes and the applicability of constraints.
        :raises ValueError: if the constraint is not fulfilled
        """
        if category == "":
            raise AASConstraintViolation(100, "category is not allowed to be an empty string")
        self._category = category

    def _get_category(self) -> Optional[str]:
        return self._category

    category = property(_get_category, _set_category)

    def _set_id_short(self, id_short: str):
        """
        Check the input string

        Constraint AASd-002: idShort of Referables shall only feature letters, digits, underscore ("_"); starting
        mandatory with a letter. I.e. [a-zA-Z][a-zA-Z0-9_]+
        Constraint AASd-003: idShort shall be matched case-insensitive
        Constraint AASd-022: idShort of non-identifiable referables shall be unique in its namespace

        :param id_short: Identifying string of the element within its name space
        :raises ValueError: if the constraint is not fulfilled
        :raises KeyError: if the new idShort causes a name collision in the parent Namespace
        """

        if id_short == self.id_short:
            return
        if id_short == "":
            raise AASConstraintViolation(100, "id_short is not allowed to be an empty string")
        test_id_short: str = str(id_short)
        if not re.fullmatch("[a-zA-Z0-9_]*", test_id_short):
            raise AASConstraintViolation(
                2,
                "The id_short must contain only letters, digits and underscore"
            )
        if not test_id_short[0].isalpha():
            raise AASConstraintViolation(
                2,
                "The id_short must start with a letter"
            )

        if self.parent is not None:
            for set_ in self.parent.namespace_element_sets:
                if set_.contains_id("id_short", id_short):
                    raise KeyError("Object with id_short '{}' is already present in the parent Namespace"
                                   .format(id_short))

            set_add_list: List[NamespaceSet] = []
            for set_ in self.parent.namespace_element_sets:
                if self in set_:
                    set_add_list.append(set_)
                    set_.discard(self)
            self._id_short = id_short
            for set_ in set_add_list:
                set_.add(self)
        # Redundant to the line above. However this way, we make sure that we really update the _id_short
        self._id_short = id_short

    def update(self,
               max_age: float = 0,
               recursive: bool = True,
               _indirect_source: bool = True) -> None:
        """
        Update the local Referable object from any underlying external data source, using an appropriate backend

        If there is no source given, it will find its next ancestor with a source and update from this source.
        If there is no source in any ancestor, this function will do nothing

        :param max_age: Maximum age of the local data in seconds. This method may return early, if the previous update
                        of the object has been performed less than `max_age` seconds ago.
        :param recursive: Also call update on all children of this object. Default is True
        :param _indirect_source: Internal parameter to avoid duplicate updating.
        :raises backends.BackendError: If no appropriate backend or the data source is not available
        """
        # TODO consider max_age
        if not _indirect_source:
            # Update was already called on an ancestor of this Referable. Only update it, if it has its own source
            if self.source != "":
                backends.get_backend(self.source).update_object(updated_object=self,
                                                                store_object=self,
                                                                relative_path=[])

        else:
            # Try to find a valid source for this Referable
            if self.source != "":
                backends.get_backend(self.source).update_object(updated_object=self,
                                                                store_object=self,
                                                                relative_path=[])
            else:
                store_object, relative_path = self.find_source()
                if store_object and relative_path is not None:
                    backends.get_backend(store_object.source).update_object(updated_object=self,
                                                                            store_object=store_object,
                                                                            relative_path=list(relative_path))

        if recursive:
            # update all the children who have their own source
            if isinstance(self, UniqueIdShortNamespace):
                for namespace_set in self.namespace_element_sets:
                    if "id_short" not in namespace_set.get_attribute_name_list():
                        continue
                    for referable in namespace_set:
                        referable.update(max_age, recursive=True, _indirect_source=False)

    def find_source(self) -> Tuple[Optional["Referable"], Optional[List[str]]]:  # type: ignore
        """
        Finds the closest source in this objects ancestors. If there is no source, returns None

        :return: Tuple with the closest ancestor with a defined source and the relative path of id_shorts to that
                 ancestor
        """
        referable: Referable = self
        relative_path: List[str] = [self.id_short]
        while referable is not None:
            if referable.source != "":
                relative_path.reverse()
                return referable, relative_path
            if referable.parent:
                assert(isinstance(referable.parent, Referable))
                referable = referable.parent
                relative_path.append(referable.id_short)
                continue
            break
        return None, None

    def update_from(self, other: "Referable", update_source: bool = False):
        """
        Internal function to updates the object's attributes from another object of a similar type.

        This function should not be used directly. It is typically used by backend implementations (database adapters,
        protocol clients, etc.) to update the object's data, after `update()` has been called.

        :param other: The object to update from
        :param update_source: Update the source attribute with the other's source attribute. This is not propagated
                              recursively
        """
        for name, var in vars(other).items():
            # do not update the parent, namespace_element_sets or source (depending on update_source parameter)
            if name in ("parent", "namespace_element_sets") or name == "source" and not update_source:
                continue
            if isinstance(var, NamespaceSet):
                # update the elements of the NameSpaceSet
                vars(self)[name].update_nss_from(var)
            else:
                vars(self)[name] = var  # that variable is not a NameSpaceSet, so it isn't Referable

    def commit(self) -> None:
        """
        Transfer local changes on this object to all underlying external data sources.

        This function commits the current state of this object to its own and each external data source of its
        ancestors. If there is no source, this function will do nothing.
        """
        current_ancestor = self.parent
        relative_path: List[str] = [self.id_short]
        # Commit to all ancestors with sources
        while current_ancestor:
            assert(isinstance(current_ancestor, Referable))
            if current_ancestor.source != "":
                backends.get_backend(current_ancestor.source).commit_object(committed_object=self,
                                                                            store_object=current_ancestor,
                                                                            relative_path=list(relative_path))
            relative_path.insert(0, current_ancestor.id_short)
            current_ancestor = current_ancestor.parent
        # Commit to own source and check if there are children with sources to commit to
        self._direct_source_commit()

    def _direct_source_commit(self):
        """
        Commits children of an ancestor recursively, if they have a specific source given
        """
        if self.source != "":
            backends.get_backend(self.source).commit_object(committed_object=self,
                                                            store_object=self,
                                                            relative_path=[])

        if isinstance(self, UniqueIdShortNamespace):
            for namespace_set in self.namespace_element_sets:
                if "id_short" not in namespace_set.get_attribute_name_list():
                    continue
                for referable in namespace_set:
                    referable._direct_source_commit()

    id_short = property(_get_id_short, _set_id_short)


_RT = TypeVar('_RT', bound=Referable)


class UnexpectedTypeError(TypeError):
    """
    Exception to be raised by :meth:`aas.model.base.AASReference.resolve` if the retrieved object has not the expected
    type.

    :ivar value: The object of unexpected type
    """
    def __init__(self, value: Referable, *args):
        super().__init__(*args)
        self.value = value


class Reference:
    """
    Reference to either a model element of the same or another AAs or to an external entity.

    A reference is an ordered list of keys, each key referencing an element. The complete list of keys may for
    example be concatenated to a path that then gives unique access to an element or entity

    :ivar: key: Ordered list of unique reference in its name space, each key referencing an element. The complete
                list of keys may for example be concatenated to a path that then gives unique access to an element
                or entity.
    :ivar: type: The type of the referenced object (additional attribute, not from the AAS Metamodel)
    """

    def __init__(self,
                 key: Tuple[Key, ...]):
        """


        TODO: Add instruction what to do after construction
        """
        self.key: Tuple[Key, ...]
        super().__setattr__('key', key)

    def __setattr__(self, key, value):
        """Prevent modification of attributes."""
        raise AttributeError('Reference is immutable')

    def __repr__(self) -> str:
        return "Reference(key={})".format(self.key)

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Reference):
            return NotImplemented
        if len(self.key) != len(other.key):
            return False
        return all(k1 == k2 for k1, k2 in zip(self.key, other.key))


class AASReference(Reference, Generic[_RT]):
    """
    Typed Reference to any referable :class:`Asset Administration Shell <aas.model.aas.AssetAdministrationShell>` object

    This is a special construct of the implementation to allow typed references and de-referencing.

    :ivar key: Ordered list of unique :class:`Keys <.Key>` in its name space, each key referencing an element.
               The complete list of keys may for example be concatenated to a path that then gives unique access to an
               element or entity.
    :ivar ~.type: The type of the referenced object (additional parameter, not from the AAS Metamodel)
                  *Initialization parameter:* `target_type`
    """
    def __init__(self,
                 key: Tuple[Key, ...],
                 target_type: Type[_RT]):
        """
        TODO: Add instruction what to do after construction
        """
        # TODO check keys for validity. GlobalReference and Fragment-Type keys are not allowed here
        super().__init__(key)
        self.type: Type[_RT]
        object.__setattr__(self, 'type', target_type)

    def resolve(self, provider_: "provider.AbstractObjectProvider") -> _RT:
        """
        Follow the :class:`~.Reference` and retrieve the :class:`~.Referable` object it points to

        :param provider_: :class:`~aas.model.provider.AbstractObjectProvider`
        :return: The referenced object (or a proxy object for it)
        :raises IndexError: If the list of keys is empty
        :raises TypeError: If one of the intermediate objects on the path is not a :class:`~aas.model.base.Namespace`
        :raises UnexpectedTypeError: If the retrieved object is not of the expected type (or one of its subclasses). The
                                     object is stored in the `value` attribute of the exception
        :raises KeyError: If the reference could not be resolved
        """
        if len(self.key) == 0:
            raise IndexError("List of keys is empty")
        # Find key index last (global) identifier-key in key list (from https://stackoverflow.com/a/6890255/10315508)
        try:
            last_identifier_index = next(i
                                         for i in reversed(range(len(self.key)))
                                         if self.key[i].get_identifier())
        except StopIteration:
            # If no identifier-key is contained in the list, we could try to resolve the path locally.
            # TODO implement local resolution
            raise NotImplementedError("We currently don't support local-only references without global identifier keys")

        resolved_keys: List[str] = []  # for more helpful error messages

        # First, resolve the identifier-key via the provider
        identifier: Identifier = self.key[last_identifier_index].get_identifier()  # type: ignore
        try:
            item: Referable = provider_.get_identifiable(identifier)
        except KeyError as e:
            raise KeyError("Could not resolve global reference key {}".format(identifier)) from e
        resolved_keys.append(str(identifier))

        # Now, follow path, given by remaining keys, recursively
        for key in self.key[last_identifier_index+1:]:
            if not isinstance(item, UniqueIdShortNamespace):
                raise TypeError("Object retrieved at {} is not a Namespace".format(" / ".join(resolved_keys)))
            try:
                item = item.get_referable(key.value)
            except KeyError as e:
                raise KeyError("Could not resolve id_short {} at {}".format(key.value, " / ".join(resolved_keys)))\
                    from e

        # Check type
        if not isinstance(item, self.type):
            raise UnexpectedTypeError(item, "Retrieved object {} is not an instance of referenced type {}"
                                            .format(item, self.type.__name__))
        return item

    def get_identifier(self) -> Identifier:
        """
        Retrieve the :class:`~.Identifier` of the :class:`~.Identifiable` object, which is referenced or in which the
        referenced :class:`~.Referable` is contained.

        :returns: :class:`~.Identifier`
        :raises ValueError: If this :class:`~.Reference` does not include a Key with global KeyType (IRDI, IRI, CUSTOM)
        """
        try:
            last_identifier = next(key.get_identifier()
                                   for key in reversed(self.key)
                                   if key.get_identifier())
            return last_identifier  # type: ignore  # MyPy doesn't get the generator expression above
        except StopIteration:
            raise ValueError("Reference cannot be represented as an Identifier, since it does not contain a Key with "
                             "global KeyType (IRDI, IRI, CUSTOM)")

    def __repr__(self) -> str:
        return "AASReference(type={}, key={})".format(self.type.__name__, self.key)

    @staticmethod
    def from_referable(referable: Referable) -> "AASReference":
        """
        Construct an :class:`~.AASReference` to a given :class:`~.Referable` AAS object

        This requires that the :class:`~.Referable` object is :class:`~.Identifiable` itself or is a
        child-, grand-child-, etc. object of an
        :class:`~.Identifiable` object. Additionally, the object must be an instance of a known :class:`~.Referable`
        type.

        :param referable: :class:`~aas.model.base.Referable` object to construct the :class:`~.AASReference` from
        :returns: Constructed :class:`~.AASReference`
        :raises ValueError: If no :class:`~aas.model.base.Identifiable` object is found while traversing the object's
                ancestors
        """
        # Get the first class from the base classes list (via inspect.getmro), that is contained in KEY_ELEMENTS_CLASSES
        from . import KEY_ELEMENTS_CLASSES
        try:
            ref_type = next(iter(t for t in inspect.getmro(type(referable)) if t in KEY_ELEMENTS_CLASSES))
        except StopIteration:
            ref_type = Referable

        ref: Referable = referable
        keys: List[Key] = []
        while True:
            keys.append(Key.from_referable(ref))
            if isinstance(ref, Identifiable):
                keys.reverse()
                return AASReference(tuple(keys), ref_type)
            if ref.parent is None or not isinstance(ref.parent, Referable):
                raise ValueError("The given Referable object is not embedded within an Identifiable object")
            ref = ref.parent


class Resource:
    """
    Resource represents an address to a file (a locator). The value is an URI that can represent an absolute or relative
    path.

    :ivar path: Path and name of the resource (with file extension). The path can be absolute or relative.
    :ivar content_type: Content type of the content of the file. The content type states which file extensions the file
                        can have.
    """
    def __init__(self, path: PathType, content_type: Optional[ContentType] = None):
        self.path: PathType = path
        self.content_type: Optional[ContentType] = content_type


class Identifiable(Referable, metaclass=abc.ABCMeta):
    """
    An element that has a globally unique :class:`~.Identifier`.

    <<abstract>>

    :ivar administration: :class:`~.AdministrativeInformation` of an identifiable element.
    :ivar ~.identification: The globally unique identification of the element.
    """
    @abc.abstractmethod
    def __init__(self):
        super().__init__()
        self.administration: Optional[AdministrativeInformation] = None
        self.identification: Identifier = Identifier("None", IdentifierType.IRDI)

    def __repr__(self) -> str:
        return "{}[{}]".format(self.__class__.__name__, self.identification)


class HasSemantics(metaclass=abc.ABCMeta):
    """
    Element that can have a semantic definition.

    <<abstract>>

    :ivar semantic_id: Identifier of the semantic definition of the element. It is called semantic id of the element.
                       The semantic id may either reference an external global id or it may reference a referable model
                       element of kind=Type that defines the semantics of the element.
    """
    @abc.abstractmethod
    def __init__(self):
        super().__init__()
        # TODO: parent can be any `Namespace`, unfortunately this definition would be incompatible with the definition
        #  of Referable.parent as `UniqueIdShortNamespace`
        self.parent: Optional[Any] = None
        self._semantic_id: Optional[Reference] = None

    @property
    def semantic_id(self):
        return self._semantic_id

    @semantic_id.setter
    def semantic_id(self, semantic_id: Optional[Reference]) -> None:
        if self.parent is not None:
            if semantic_id is not None:
                for set_ in self.parent.namespace_element_sets:
                    if set_.contains_id("semantic_id", semantic_id):
                        raise KeyError("Object with semantic_id '{}' is already present in the parent Namespace"
                                       .format(semantic_id))
            set_add_list: List[NamespaceSet] = []
            for set_ in self.parent.namespace_element_sets:
                if self in set_:
                    set_add_list.append(set_)
                    set_.discard(self)
            self._semantic_id = semantic_id
            for set_ in set_add_list:
                set_.add(self)
        # Redundant to the line above. However this way, we make sure that we really update the _semantic_id
        self._semantic_id = semantic_id


class Extension(HasSemantics):
    """
    Single extension of an element

    :ivar name: An extension of the element.
    :ivar value_type: Type (:class:`~.DataTypeDef`) of the value of the extension. Default: xsd:string
    :ivar value: Value (:class:`~.ValueDataType`) of the extension
    :ivar refers_to: :class:`~.Reference` to an element the extension refers to
    :ivar semantic_id: The semantic_id defined in the :class:`~.HasSemantics` class.
    """

    def __init__(self,
                 name: str,
                 value_type: Optional[DataTypeDef] = None,
                 value: Optional[ValueDataType] = None,
                 refers_to: Optional[Reference] = None,
                 semantic_id: Optional[Reference] = None):
        """
        Initializer of Extension

        :param name: An extension of the element.
        :param value_type: Type of the value of the extension. Default: xsd:string
        :param value: Value of the extension
        :param refers_to: Reference to an element the extension refers to
        :param semantic_id: The semantic_id defined in the HasSemantics class.
        :raises ValueError: if the value_type is None and a value is set
        """
        super().__init__()
        self.parent: Optional[HasExtension] = None
        self._name: str
        self.name: str = name
        self.value_type: Optional[Type[datatypes.AnyXSDType]] = value_type
        self._value: Optional[ValueDataType]
        self.value = value
        self.refers_to: Optional[Reference] = refers_to
        self.semantic_id: Optional[Reference] = semantic_id

    def __repr__(self) -> str:
        return "Extension(name={})".format(self.name)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value) -> None:
        if value is None:
            self._value = None
        else:
            if self.value_type is None:
                raise ValueError('ValueType must be set, if value is not None')
            self._value = datatypes.trivial_cast(value, self.value_type)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        if self.parent is not None:
            for set_ in self.parent.namespace_element_sets:
                if set_.contains_id("name", name):
                    raise KeyError("Object with name '{}' is already present in the parent Namespace"
                                   .format(name))
            set_add_list: List[NamespaceSet] = []
            for set_ in self.parent.namespace_element_sets:
                if self in set_:
                    set_add_list.append(set_)
                    set_.discard(self)
            self._name = name
            for set_ in set_add_list:
                set_.add(self)
        # Redundant to the line above. However this way, we make sure that we really update the _name
        self._name = name


class HasKind(metaclass=abc.ABCMeta):
    """
    An element with a kind is an element that can either represent a type or an instance.
    Default for an element is that it is representing an instance.

    <<abstract>>

    :ivar _kind: Kind of the element: either type or instance. Default = :attr:`~ModelingKind.INSTANCE`.
    """
    @abc.abstractmethod
    def __init__(self):
        super().__init__()
        self._kind: ModelingKind = ModelingKind.INSTANCE

    @property
    def kind(self):
        return self._kind


class Qualifiable(Namespace, metaclass=abc.ABCMeta):
    """
    Abstract baseclass for all objects which form a Namespace to hold :class:`~.Qualifier` objects and resolve them by
    their type.

    <<abstract>>

    :ivar namespace_element_sets: A list of all :class:`NamespaceSets <.NamespaceSet>` of this Namespace
    :ivar qualifier: Unordered list of :class:`Qualifiers <~.Qualifier>` that gives additional qualification of a
        qualifiable element.
    """
    @abc.abstractmethod
    def __init__(self):
        super().__init__()
        self.namespace_element_sets: List[NamespaceSet] = []
        self.qualifier: NamespaceSet[Qualifier]

    def get_qualifier_by_type(self, qualifier_type: QualifierType) -> "Qualifier":
        """
        Find a :class:`~.Qualifier` in this Namespace by its type

        :raises KeyError: If no such :class:`~.Qualifier` can be found
        """
        return super()._get_object(Qualifiable, "type", qualifier_type)

    def add_qualifier(self, qualifier: "Qualifier") -> None:
        """
        Add a :class:`~.Qualifier` to this Namespace

        :param qualifier: The :class:`~.Qualifier` to add
        :raises KeyError: If a qualifier with the same type is already present in this namespace
        :raises ValueError: If the passed object already has a parent namespace
        """
        return super()._add_object("type", qualifier)

    def remove_qualifier_by_type(self, qualifier_type: QualifierType) -> None:
        """
        Remove a :class:`~.Qualifier` from this Namespace by its type

        :raises KeyError: If no such :class:`~.Qualifier` can be found
        """
        return super()._remove_object(Qualifiable, "type", qualifier_type)


class Qualifier(HasSemantics):
    """
    A qualifier is a type-value pair that makes additional statements w.r.t. the value of the element.

    *Constraint AASd-006:* if both, the value and the valueId are present, then the value needs to be
    identical to the value of the referenced coded value in Qualifier/valueId.

    :ivar type: The type (:class:`~.QualifierType`) of the qualifier that is applied to the element.
    :ivar value_type: Data type (:class:`~.DataTypeDef`) of the qualifier value
    :ivar value: The value (:class:`~.ValueDataType`) of the qualifier.
    :ivar value_id: :class:`~.Reference` to the global unique id of a coded value.
    :ivar semantic_id: The semantic_id defined in :class:`~.HasSemantics`.
    """

    def __init__(self,
                 type_: QualifierType,
                 value_type: DataTypeDef,
                 value: Optional[ValueDataType] = None,
                 value_id: Optional[Reference] = None,
                 semantic_id: Optional[Reference] = None):
        """
        TODO: Add instruction what to do after construction
        """
        super().__init__()
        self.parent: Optional[Qualifiable] = None
        self._type: QualifierType
        self.type: QualifierType = type_
        self.value_type: Type[datatypes.AnyXSDType] = value_type
        self._value: Optional[ValueDataType] = datatypes.trivial_cast(value, value_type) if value is not None else None
        self.value_id: Optional[Reference] = value_id
        self.semantic_id: Optional[Reference] = semantic_id

    def __repr__(self) -> str:
        return "Qualifier(type={})".format(self.type)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value) -> None:
        if value is None:
            self._value = None
        else:
            self._value = datatypes.trivial_cast(value, self.value_type)

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, type_: QualifierType) -> None:
        if self.parent is not None:
            for set_ in self.parent.namespace_element_sets:
                if set_.contains_id("type", type_):
                    raise KeyError("Object with type '{}' is already present in the parent Namespace"
                                   .format(type_))
            set_add_list: List[NamespaceSet] = []
            for set_ in self.parent.namespace_element_sets:
                if self in set_:
                    set_add_list.append(set_)
                    set_.discard(self)
            self._type = type_
            for set_ in set_add_list:
                set_.add(self)
        # Redundant to the line above. However this way, we make sure that we really update the _type
        self._type = type_


class ValueReferencePair:
    """
    A value reference pair within a value list. Each value has a global unique id defining its semantic.

    <<DataType>>

    :ivar value: The value of the referenced concept definition of the value in value_id
    :ivar value_id: Global unique id of the value.
    :ivar value_type: XSD datatype of the value (this is not compliant to the DotAAS meta model)
    """

    def __init__(self,
                 value_type: DataTypeDef,
                 value: ValueDataType,
                 value_id: Reference):
        """


        TODO: Add instruction what to do after construction
        """
        self.value_type: Type[datatypes.AnyXSDType] = value_type
        self.value_id: Reference = value_id
        self._value: ValueDataType = datatypes.trivial_cast(value, value_type)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value) -> None:
        if value is None:
            raise AttributeError('Value can not be None')
        else:
            self._value = datatypes.trivial_cast(value, self.value_type)

    def __repr__(self) -> str:
        return "ValueReferencePair(value_type={}, value={}, value_id={})".format(self.value_type,
                                                                                 self.value,
                                                                                 self.value_id)


ValueList = Set[ValueReferencePair]


class UniqueIdShortNamespace(Namespace, metaclass=abc.ABCMeta):
    """
    Abstract baseclass for all objects which form a Namespace to hold :class:`~.Referable` objects and resolve them by
    their id_short.

    A Namespace can contain multiple :class:`NamespaceSets <~.NamespaceSet>`, which contain :class:`~.Referable` objects
    of different types. However, the id_short of each object must be unique across all NamespaceSets of one Namespace.



    :ivar namespace_element_sets: A list of all :class:`NamespaceSets <.NamespaceSet>` of this Namespace
    """
    @abc.abstractmethod
    def __init__(self) -> None:
        self.namespace_element_sets: List[NamespaceSet] = []

    def get_referable(self, id_short: str) -> Referable:
        """
        Find a :class:`~.Referable` in this Namespace by its id_short

        :param id_short: id_short
        :returns: :class:`~.Referable`
        :raises KeyError: If no such :class:`~.Referable` can be found
        """
        return super()._get_object(Referable, "id_short", id_short)

    def add_referable(self, referable: Referable) -> None:
        """
        Add a :class:`~.Referable` to this Namespace

        :param referable: The :class:`~.Referable` to add
        :raises KeyError: If a :class:`~.Referable` with the same name is already present in this namespace
        :raises ValueError: If the given :class:`~.Referable` already has a parent namespace
        """
        return super()._add_object("id_short", referable)

    def remove_referable(self, id_short: str) -> None:
        """
        Remove a :class:`~.Referable` from this Namespace by its `id_short`

        :param id_short: id_short
        :raises KeyError: If no such :class:`~.Referable` can be found
        """
        return super()._remove_object(Referable, "id_short", id_short)

    def __iter__(self) -> Iterator[Referable]:
        namespace_set_list: List[NamespaceSet] = []
        for namespace_set in self.namespace_element_sets:
            if len(namespace_set) == 0:
                namespace_set_list.append(namespace_set)
                continue
            if "id_short" in namespace_set.get_attribute_name_list():
                namespace_set_list.append(namespace_set)
        return itertools.chain.from_iterable(namespace_set_list)


class UniqueSemanticIdNamespace(Namespace, metaclass=abc.ABCMeta):
    """
    Abstract baseclass for all objects which form a Namespace to hold HasSemantics objects and resolve them by their
    their semantic_id.

    A Namespace can contain multiple NamespaceSets, which contain HasSemantics objects of different types. However, the
    the semantic_id of each object must be unique across all NamespaceSets of one Namespace.

    :ivar namespace_element_sets: A list of all NamespaceSets of this Namespace
    """
    @abc.abstractmethod
    def __init__(self) -> None:
        self.namespace_element_sets: List[NamespaceSet] = []

    def get_object_by_semantic_id(self, semantic_id: Reference) -> HasSemantics:
        """
        Find an HasSemantics in this Namespaces by its semantic_id

        :raises KeyError: If no such HasSemantics can be found
        """
        return super()._get_object(HasSemantics, "semantic_id", semantic_id)

    def remove_object_by_semantic_id(self, semantic_id: Reference) -> None:
        """
        Remove an HasSemantics from this Namespace by its semantic_id

        :raises KeyError: If no such HasSemantics can be found
        """
        return super()._remove_object(HasSemantics, "semantic_id", semantic_id)


ATTRIBUTE_TYPES = Union[str, Reference, QualifierType]


class NamespaceSet(MutableSet[_NSO], Generic[_NSO]):
    """
    Helper class for storing AAS objects of a given type in a Namespace and find them by their unique attribute.

    This class behaves much like a set of AAS objects of a defined type, but uses dicts internally to rapidly
    find those objects by their unique attribute. Additionally, it manages the `parent` attribute of the stored
    AAS objects and ensures the uniqueness of their attribute within the Namespace.

    Use `add()`, `remove()`, `pop()`, `discard()`, `clear()`, `len()`, `x in` checks and iteration  just like on a
    normal set of AAS objects. To get an AAS object by its attribute, use `get_object()` or `get()` (the latter one
    allows a default argument and returns None instead of raising a KeyError). As a bonus, the `x in` check supports
    checking for existence of attribute *or* a concrete AAS object.

    :ivar parent: The Namespace this set belongs to

    To initialize, use the following parameters:

    :param parent: The Namespace this set belongs to
    :param attribute_names: List of attribute names, for which objects should be unique in the set. The bool flag
        indicates if the attribute should be matched case-sensitive (true) or case-insensitive (false)
    :param items: A given list of AAS items to be added to the set

    :raises KeyError: When `items` contains multiple objects with same unique attribute
    """
    def __init__(self, parent: Union[UniqueIdShortNamespace, UniqueSemanticIdNamespace, Qualifiable, HasExtension],
                 attribute_names: List[Tuple[str, bool]], items: Iterable[_NSO] = ()) -> None:
        """
        Initialize a new NamespaceSet.

        This initializer automatically takes care of adding this set to the `namespace_element_sets` list of the
        Namespace.

        :param parent: The Namespace this set belongs to
        :attribute_names: List of attribute names, for which objects should be unique in the set. The bool flag
                          indicates if the attribute should be matched case-sensitive (true) or case-insensitive (false)
        :param items: A given list of AAS items to be added to the set
        :raises KeyError: When `items` contains multiple objects with same unique attribute
        """
        self.parent = parent
        parent.namespace_element_sets.append(self)
        self._backend: Dict[str, Tuple[Dict[ATTRIBUTE_TYPES, _NSO], bool]] = {}
        for name, case_sensitive in attribute_names:
            self._backend[name] = ({}, case_sensitive)
        try:
            for i in items:
                self.add(i)
        except Exception:
            # Do a rollback, when an exception occurs while adding items
            self.clear()
            raise

    @staticmethod
    def _get_attribute(x: object, attr_name: str, case_sensitive: bool):
        attr_value = getattr(x, attr_name)
        return attr_value if case_sensitive or not isinstance(attr_value, str) else attr_value.upper()

    def get_attribute_name_list(self) -> List[str]:
        return list(self._backend.keys())

    def contains_id(self, attribute_name: str, identifier: ATTRIBUTE_TYPES) -> bool:
        try:
            backend, case_sensitive = self._backend[attribute_name]
        except KeyError:
            return False
        # if the identifier is not a string we ignore the case sensitivity
        if case_sensitive or not isinstance(identifier, str):
            return identifier in backend
        return identifier.upper() in backend

    def __contains__(self, obj: object) -> bool:
        attr_name = next(iter(self._backend))
        try:
            attr_value = self._get_attribute(obj, attr_name, self._backend[attr_name][1])
        except AttributeError:
            return False
        return self._backend[attr_name][0].get(attr_value) is obj

    def __len__(self) -> int:
        return len(self._backend[next(iter(self._backend))][0])

    def __iter__(self) -> Iterator[_NSO]:
        return iter(self._backend[next(iter(self._backend))][0].values())

    def add(self, value: _NSO):
        for set_ in self.parent.namespace_element_sets:
            for attr_name, (backend, case_sensitive) in set_._backend.items():
                if hasattr(value, attr_name):
                    if self._get_attribute(value, attr_name, case_sensitive) in backend:
                        raise KeyError("Object with attribute (name='{}', value='{}') is already present in {}"
                                       .format(attr_name, str(getattr(value, attr_name)),
                                               "this set of objects"
                                               if set_ is self else "another set in the same namespace"))
        if value.parent is not None and value.parent is not self.parent:
            raise ValueError("Object has already a parent, but it must not be part of two namespaces.")
            # TODO remove from current parent instead (allow moving)?
        value.parent = self.parent
        for attr_name, (backend, case_sensitive) in self._backend.items():
            backend[self._get_attribute(value, attr_name, case_sensitive)] = value

    def remove_by_id(self, attribute_name: str, identifier: ATTRIBUTE_TYPES) -> None:
        item = self.get_object_by_attribute(attribute_name, identifier)
        self.remove(item)

    def remove(self, item: _NSO) -> None:
        item_found = False
        for attr_name, (backend, case_sensitive) in self._backend.items():
            item_in_dict = backend[self._get_attribute(item, attr_name, case_sensitive)]
            if item_in_dict is item:
                item_found = True
                continue
        if not item_found:
            raise KeyError("Object not found in NamespaceDict")
        item.parent = None
        for attr_name, (backend, case_sensitive) in self._backend.items():
            del backend[self._get_attribute(item, attr_name, case_sensitive)]

    def discard(self, x: _NSO) -> None:
        if x not in self:
            return
        self.remove(x)

    def pop(self) -> _NSO:
        _, value = self._backend[next(iter(self._backend))][0].popitem()
        value.parent = None
        return value

    def clear(self) -> None:
        for attr_name, (backend, case_sensitive) in self._backend.items():
            for value in backend.values():
                value.parent = None
        for attr_name, (backend, case_sensitive) in self._backend.items():
            backend.clear()

    def get_object_by_attribute(self, attribute_name: str, attribute_value: ATTRIBUTE_TYPES) -> _NSO:
        """
        Find an object in this set by its unique attribute

        :raises KeyError: If no such object can be found
        """
        backend, case_sensitive = self._backend[attribute_name]
        return backend[attribute_value if case_sensitive else attribute_value.upper()]  # type: ignore

    def get(self, attribute_name: str, attribute_value: str, default: Optional[_NSO] = None) -> Optional[_NSO]:
        """
        Find an object in this set by its attribute, with fallback parameter

        :param attribute_name: name of the attribute to search for
        :param attribute_value: value of the attribute to search for
        :param default: An object to be returned, if no object with the given attribute is found
        :return: The AAS object with the given attribute in the set. Otherwise the `default` object or None, if
                 none is given.
        """
        backend, case_sensitive = self._backend[attribute_name]
        return backend.get(attribute_value if case_sensitive else attribute_value.upper(), default)

    # Todo: Implement function including tests
    def update_nss_from(self, other: "NamespaceSet"):
        """
        Update a NamespaceSet from a given NamespaceSet.

        WARNING: By updating, the "other" NamespaceSet gets destroyed.

        :param other: The NamespaceSet to update from
        """
        objects_to_add: List[_NSO] = []  # objects from the other nss to add to self
        objects_to_remove: List[_NSO] = []  # objects to remove from self
        for other_object in other:
            try:
                if isinstance(other_object, Referable):
                    backend, case_sensitive = self._backend["id_short"]
                    referable = backend[other_object.id_short if case_sensitive else other_object.id_short.upper()]
                    referable.update_from(other_object, update_source=True)  # type: ignore
                elif isinstance(other_object, Qualifier):
                    backend, case_sensitive = self._backend["type"]
                    qualifier = backend[other_object.type if case_sensitive else other_object.type.upper()]
                    # qualifier.update_from(other_object, update_source=True) # TODO: What should happend here?
                elif isinstance(other_object, Extension):
                    backend, case_sensitive = self._backend["name"]
                    extension = backend[other_object.name if case_sensitive else other_object.name.upper()]
                    # extension.update_from(other_object, update_source=True) # TODO: What should happend here?
                else:
                    raise TypeError("Type not implemented")
            except KeyError:
                # other object is not in NamespaceSet
                objects_to_add.append(other_object)
        for attr_name, (backend, case_sensitive) in self._backend.items():
            for attr_name_other, (backend_other, case_sensitive_other) in other._backend.items():
                if attr_name is attr_name_other:
                    for item in backend.values():
                        if not backend_other.get(self._get_attribute(item, attr_name, case_sensitive)):
                            # referable does not exist in the other NamespaceSet
                            objects_to_remove.append(item)
        for object_to_add in objects_to_add:
            other.remove(object_to_add)
            self.add(object_to_add)  # type: ignore
        for object_to_remove in objects_to_remove:
            self.remove(object_to_remove)  # type: ignore


class OrderedNamespaceSet(NamespaceSet[_NSO], MutableSequence[_NSO], Generic[_NSO]):
    """
    A specialized version of :class:`~.NamespaceSet`, that keeps track of the order of the stored
    :class:`~.Referable` objects.

    Additionally to the MutableSet interface of :class:`~.NamespaceSet`, this class provides a set-like interface
    (actually it is derived from MutableSequence). However, we don't permit duplicate entries in the ordered list of
    objects.
    """
    def __init__(self, parent: Union[UniqueIdShortNamespace, UniqueSemanticIdNamespace, Qualifiable, HasExtension],
                 attribute_names: List[Tuple[str, bool]], items: Iterable[_NSO] = ()) -> None:
        """
        Initialize a new OrderedNamespaceSet.

        This initializer automatically takes care of adding this set to the `namespace_element_sets` list of the
        Namespace.

        :param parent: The Namespace this set belongs to
        :attribute_names: Dict of attribute names, for which objects should be unique in the set. The bool flag
                          indicates if the attribute should be matched case-sensitive (true) or case-insensitive (false)
        :param items: A given list of Referable items to be added to the set
        :raises KeyError: When `items` contains multiple objects with same id_short
        """
        self._order: List[_NSO] = []
        super().__init__(parent, attribute_names, items)

    def __iter__(self) -> Iterator[_NSO]:
        return iter(self._order)

    def add(self, value: _NSO):
        super().add(value)
        self._order.append(value)

    def remove(self, item: Union[Tuple[str, ATTRIBUTE_TYPES], _NSO]):
        if isinstance(item, tuple):
            item = self.get_object_by_attribute(item[0], item[1])
        super().remove(item)
        self._order.remove(item)

    def pop(self, i: Optional[int] = None) -> _NSO:
        if i is None:
            value = super().pop()
            self._order.remove(value)
        else:
            value = self._order.pop(i)
            super().remove(value)
        return value

    def clear(self) -> None:
        super().clear()
        self._order.clear()

    def insert(self, index: int, object_: _NSO) -> None:
        super().add(object_)
        self._order.insert(index, object_)

    @overload
    def __getitem__(self, i: int) -> _NSO: ...

    @overload
    def __getitem__(self, s: slice) -> MutableSequence[_NSO]: ...

    def __getitem__(self, s: Union[int, slice]) -> Union[_NSO, MutableSequence[_NSO]]:
        return self._order[s]

    @overload
    def __setitem__(self, i: int, o: _NSO) -> None: ...

    @overload
    def __setitem__(self, s: slice, o: Iterable[_NSO]) -> None: ...

    def __setitem__(self, s, o) -> None:
        if isinstance(s, int):
            deleted_items = [self._order[s]]
            super().add(o)
            self._order[s] = o
        else:
            deleted_items = self._order[s]
            new_items = itertools.islice(o, len(deleted_items))
            successful_new_items = []
            try:
                for i in new_items:
                    super().add(i)
                    successful_new_items.append(i)
            except Exception:
                # Do a rollback, when an exception occurs while adding items
                for i in successful_new_items:
                    super().remove(i)
                raise
            self._order[s] = new_items
        for i in deleted_items:
            super().remove(i)

    @overload
    def __delitem__(self, i: int) -> None: ...

    @overload
    def __delitem__(self, i: slice) -> None: ...

    def __delitem__(self, i: Union[int, slice]) -> None:
        if isinstance(i, int):
            i = slice(i, i+1)
        for o in self._order[i]:
            super().remove(o)
        del self._order[i]


class IdentifierKeyValuePair:
    """
    An IdentifierKeyValuePair describes a generic identifier as key-value pair

    :ivar key: Key of the identifier
    :ivar value: The value of the identifier with the corresponding key.
    :ivar external_subject_id: The (external) subject the key belongs to or has meaning to.

    :ivar semantic_id: The semantic_id defined in the :class:`~.HasSemantics` class.
    """

    # TODO make IdentifierKeyValuePair derive from HasSemantics
    def __init__(self,
                 key: str,
                 value: str,
                 external_subject_id: Reference,
                 semantic_id: Optional[Reference] = None):
        super().__init__()
        if key == "":
            raise ValueError("key is not allowed to be an empty string")
        if value == "":
            raise ValueError("value is not allowed to be an empty string")
        self.key: str
        self.value: str
        self.external_subject_id: Reference

        super().__setattr__('key', key)
        super().__setattr__('value', value)
        super().__setattr__('external_subject_id', external_subject_id)

    def __setattr__(self, key, value):
        """Prevent modification of attributes."""
        raise AttributeError('IdentifierKeyValuePair is immutable')

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, IdentifierKeyValuePair):
            return NotImplemented
        return (self.key == other.key
                and self.value == other.value
                and self.external_subject_id == other.external_subject_id)

    def __hash__(self):
        return hash((self.key, self.value, self.external_subject_id))

    def __repr__(self) -> str:
        return "IdentifierKeyValuePair(key={}, value={}, external_subject_id={})".format(self.key, self.value,
                                                                                         self.external_subject_id)


class AASConstraintViolation(Exception):
    """
    An Exception to be raised if an AASd-Constraint defined in the metamodel (Details of the Asset Administration Shell)
    is violated

    :ivar constraint_id: The ID of the constraint that is violated
    :ivar message: The error message of the Exception
    """
    def __init__(self, constraint_id: int, message: str):
        self.constraint_id: int = constraint_id
        self.message: str = message + " (Constraint AASd-" + str(constraint_id).zfill(3) + ")"
        super().__init__(self.message)
