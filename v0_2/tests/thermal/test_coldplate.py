from dataclasses import replace
from itertools import pairwise

import pytest
from v0_2.thermal.coldplate import ManufacturerColdplateSchema, ZeroFlowPolicy
from v0_2.thermal.fixtures import coldplate_edge, coldplate_model, flow, gpu_chain
from v0_2.thermal.provenance import fixture_parameter as p
from v0_2.thermal.topology import ThermalTopology
from v0_2.thermal.validity import ThermalError, ValidityStatus


def test_flow_monotonicity_and_positive_conduction_bound():
    model = coldplate_model()
    values = [model.evaluate(320.0, 300.0, flow(m)) for m in (0.01, 0.05, 0.1, 0.2, 0.5)]
    assert all(
        a.endpoint_resistance_k_w >= b.endpoint_resistance_k_w
        and a.heat_transfer_w <= b.heat_transfer_w
        for a, b in pairwise(values)
    )
    assert all(v.endpoint_resistance_k_w >= model.conduction_r.value for v in values)
    assert all(v.coolant_side_state == 300 for v in values)


def test_valid_generic_endpoints_and_distinct_tim():
    f = gpu_chain()
    cp = f.topology.interfaces[2]
    assert cp.hot_node_id == "plate" and cp.cold_node_id == "coolant"
    assert not set(cp.included_layer_ids) & set(f.topology.interfaces[1].included_layer_ids)


def test_manufacturer_tim_overlap_fails_preflight():
    f = gpu_chain()
    original = f.topology.interfaces[2].resistance_model
    d = replace(
        original.definition,
        rth_definition="DEVICE_TO_COOLANT",
        manufacturer_rth_definition="DEVICE_TO_COOLANT",
        manufacturer_measurement_hot_endpoint="plate",
        manufacturer_measurement_cold_endpoint="coolant",
        included_layers=("gpu:TIM_CONTACT", "plate:PLATE_CONVECTION"),
    )
    imported = ManufacturerColdplateSchema(d, original.provenance)
    with pytest.raises(ThermalError, match="THERMAL_RESISTANCE_OVERLAP"):
        ThermalTopology(
            f.topology.initial_state,
            (*f.topology.interfaces[:2], coldplate_edge(imported), *f.topology.interfaces[3:]),
            f.topology.device_cvs,
        )


def test_manufacturer_endpoint_mismatch_rejected():
    d = coldplate_model().definition
    with pytest.raises(ThermalError, match="IMPORT_CONFLICT"):
        replace(
            d,
            manufacturer_rth_definition=d.rth_definition,
            manufacturer_measurement_hot_endpoint="die",
            manufacturer_measurement_cold_endpoint="coolant",
        )


def test_generic_upstream_layer_rejected():
    model = coldplate_model()
    with pytest.raises(ThermalError, match="THERMAL_RESISTANCE_OVERLAP"):
        replace(model, definition=replace(model.definition, included_layers=("gpu:TIM_CONTACT",)))


def test_generic_missing_layer_rejected():
    model = coldplate_model()
    with pytest.raises(ThermalError, match="IMPORT_CONFLICT"):
        replace(
            model, definition=replace(model.definition, included_layers=("plate:PLATE_CONDUCTION",))
        )


def test_aliased_duplicate_layer_rejected():
    d = coldplate_model().definition
    with pytest.raises(ThermalError, match="THERMAL_RESISTANCE_OVERLAP"):
        replace(d, included_layers=("plate:PLATE_CONDUCTION", "plate:PLATE_INTERNAL_CONDUCTION"))


def test_alias_cannot_hide_topology_overlap():
    f = gpu_chain()
    alias = replace(f.topology.interfaces[0], included_layer_ids=("plate:PLATE_CONDUCTION",))
    with pytest.raises(ThermalError, match="THERMAL_RESISTANCE_OVERLAP"):
        replace(f.topology, interfaces=(alias, *f.topology.interfaces[1:]))


def test_reserved_node_cv_id_rejected():
    with pytest.raises(ThermalError, match="ENERGY_TOPOLOGY_FAIL"):
        replace(gpu_chain().topology, device_cvs=(("node:die", ("die",)),))


def test_generic_wrong_node_type_rejected():
    f = gpu_chain()
    model = coldplate_model(hot="die")
    with pytest.raises(ThermalError, match="IMPORT_CONFLICT"):
        ThermalTopology(
            f.topology.initial_state,
            (*f.topology.interfaces[:2], coldplate_edge(model), *f.topology.interfaces[3:]),
            f.topology.device_cvs,
        )


def test_zero_flow_default_invalid():
    with pytest.raises(ThermalError) as error:
        coldplate_model().evaluate(320.0, 300.0, flow(0.0))
    assert error.value.status == ValidityStatus.MODEL_INVALID


def test_zero_flow_explicit_finite_model():
    model = replace(
        coldplate_model(),
        zero_policy=ZeroFlowPolicy.ZERO_FLOW_VALID_MODEL,
        no_flow_resistance=p("qualified_fixture_no_flow_R", 2.0, "K/W"),
    )
    result = model.evaluate(320.0, 300.0, flow(0.0))
    assert result.endpoint_resistance_k_w == 2.0
    assert result.heat_transfer_w == 10.0
    assert model.no_flow_resistance.calibration_status == "UNVALIDATED"


def test_zero_flow_missing_qualified_model_rejected():
    with pytest.raises(ThermalError, match="ZERO_FLOW_POLICY"):
        replace(coldplate_model(), zero_policy=ZeroFlowPolicy.ZERO_FLOW_VALID_MODEL)


def test_reverse_signed_heat_no_clamp():
    m = coldplate_model()
    assert (
        m.evaluate(290.0, 310.0, flow()).heat_transfer_w
        == -m.evaluate(310.0, 290.0, flow()).heat_transfer_w
    )


@pytest.mark.parametrize("value", [0.009, 0.501])
def test_flow_outside_range(value):
    with pytest.raises(ThermalError) as error:
        coldplate_model().evaluate(320.0, 300.0, flow(value))
    assert error.value.status == ValidityStatus.MODEL_OUT_OF_RANGE


@pytest.mark.parametrize("temp", [249.0, 501.0])
def test_temperature_outside_range(temp):
    with pytest.raises(ThermalError, match="COLDPLATE_T_OUT_OF_RANGE"):
        coldplate_model().evaluate(temp, 300.0, flow())


def test_coolant_and_reverse_flow_invalid():
    with pytest.raises(ThermalError, match="COOLANT_MISMATCH"):
        coldplate_model().evaluate(320.0, 300.0, flow(0.1, "unknown_glycol"))
    with pytest.raises(ThermalError, match="REVERSE_FLOW"):
        coldplate_model().evaluate(320.0, 300.0, flow(-0.1))


def test_heat_load_range_enforced():
    with pytest.raises(ThermalError, match="HEAT_LOAD_OUT_OF_RANGE"):
        replace(coldplate_model(), heat_load_range=(0.0, 10.0)).evaluate(320.0, 300.0, flow())
