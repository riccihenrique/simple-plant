"""Number platform for simple_plant."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import UnitOfTime

from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import SimplePlantCoordinator


ENTITY_DESCRIPTIONS = (
    NumberEntityDescription(
        key="days_between_waterings",
        translation_key="days_between_waterings",
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        icon="mdi:counter",
        native_step=0,
        native_min_value=1,
        native_max_value=60,
        native_unit_of_measurement=UnitOfTime.DAYS,
    ),
    NumberEntityDescription(
        key="days_between_fertilizations",
        translation_key="days_between_fertilizations",
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        icon="mdi:counter",
        native_step=0,
        native_min_value=1,
        native_max_value=365,
        native_unit_of_measurement=UnitOfTime.DAYS,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number platform."""
    fertilization_enabled = entry.data.get("enable_fertilization", False)
    async_add_entities(
        SimplePlantNumber(hass, entry, entity_description)
        for entity_description in ENTITY_DESCRIPTIONS
        if fertilization_enabled or entity_description.key != "days_between_fertilizations"
    )


class SimplePlantNumber(NumberEntity):
    """simple_plant number class."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_native_min_value = 1
    _attr_native_max_value = 60
    _attr_native_step = 1

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        description: NumberEntityDescription,
    ) -> None:
        """Initialize the number class."""
        super().__init__()
        self._hass = hass
        self._entry = entry
        self.entity_description = description
        self.coordinator: SimplePlantCoordinator = hass.data[DOMAIN][entry.entry_id]

        device = self.coordinator.device

        self.entity_id = f"number.{DOMAIN}_{description.key}_{device}"
        self._attr_unique_id = f"{DOMAIN}_{description.key}_{device}"

        # Override min/max from description if provided
        if description.native_min_value is not None:
            self._attr_native_min_value = description.native_min_value
        if description.native_max_value is not None:
            self._attr_native_max_value = description.native_max_value

        # set value — default to 30 days if not configured (migration from older entries)
        self._fallback_value = entry.data.get(description.key) or 30

        # Set up device info
        self._attr_device_info = self.coordinator.device_info

    @property
    def device(self) -> str | None:
        """Return the device name."""
        return self.coordinator.device

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        await super().async_added_to_hass()

        def warning(msg: str) -> None:
            LOGGER.warning("%s :%s", self.unique_id, msg)

        if self.coordinator.data is None:
            warning("Coordinator not ready at initialization")
            return
        data = self.coordinator.data.get(self.unique_id)
        if data is None:
            if self._fallback_value is None:
                warning("Initialization failed as _fallback_value is None")
                return
            await self.async_set_native_value(self._fallback_value)
            return
        await self.async_set_native_value(float(data))

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._attr_native_value = value
        self.async_write_ha_state()

        # Save to persistent storage
        if self.unique_id is not None:
            await self.coordinator.async_store_value(self.unique_id, str(value))
