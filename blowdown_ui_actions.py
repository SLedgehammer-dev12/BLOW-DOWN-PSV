from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BlowdownExecutionResult:
    status: str
    engine_name: str
    required_area_m2: float | None = None
    total_selected_area_m2: float | None = None
    selected_valve: object | None = None
    workflow_result: dict | None = None
    sim_df: object | None = None
    fallback_used: bool = False


def execute_blowdown_ui_flow(
    *,
    user_inputs: dict,
    native_engine_name: str,
    update_progress_ui,
    abort_flag,
    load_api526_data,
    load_api6d_data,
    size_area_fn,
    select_standard_valve_fn,
    run_engine_fn,
    build_report_fn,
):
    update_progress_ui(10, 100, "Giriş parametreleri doğrulanıyor...")
    engine_name = user_inputs.get("solver_engine", native_engine_name)

    required_area_m2 = size_area_fn(engine_name, user_inputs, update_progress_ui, abort_flag)
    if abort_flag.is_set() or required_area_m2 is None:
        update_progress_ui(0, 100, "Simulasyon durduruldu.")
        return BlowdownExecutionResult(status="aborted", engine_name=engine_name)

    valve_count = user_inputs["valve_count"]
    required_area_per_valve_mm2 = (required_area_m2 / valve_count) * 1e6

    is_psv = "API 526" in user_inputs["valve_type"]
    valve_data = load_api526_data() if is_psv else load_api6d_data()
    selected_valve, fallback_used = select_standard_valve_fn(valve_data, required_area_per_valve_mm2)
    total_selected_area_m2 = (selected_valve.area_mm2 / 1e6) * valve_count

    update_progress_ui(80, 100, f"{engine_name} sonuc profili isleniyor...")
    sim_df = run_engine_fn(engine_name, user_inputs, total_selected_area_m2, update_progress_ui, abort_flag)
    if sim_df is None:
        return BlowdownExecutionResult(
            status="aborted",
            engine_name=engine_name,
            required_area_m2=required_area_m2,
            total_selected_area_m2=total_selected_area_m2,
            selected_valve=selected_valve,
            fallback_used=fallback_used,
        )

    update_progress_ui(100, 100, "Simulasyon basariyla tamamlandi!")

    if is_psv:
        valve_type_label = f"{selected_valve.size_in} {selected_valve.letter} ({selected_valve.size_dn})"
        valve_type_description = "PSV/PRV Orifis"
    else:
        valve_type_label = f"{selected_valve.size_in} ({selected_valve.size_dn})"
        valve_type_description = "Kuresel Vana (API 6D)"

    workflow_result = build_report_fn(
        sim_df=sim_df,
        inputs=user_inputs,
        engine_name=engine_name,
        selected_valve=selected_valve,
        valve_type_label=valve_type_label,
        valve_type_description=valve_type_description,
        valve_count=valve_count,
        required_area_m2=required_area_m2,
        total_selected_area_m2=total_selected_area_m2,
    )

    return BlowdownExecutionResult(
        status="completed",
        engine_name=engine_name,
        required_area_m2=required_area_m2,
        total_selected_area_m2=total_selected_area_m2,
        selected_valve=selected_valve,
        workflow_result=workflow_result,
        sim_df=sim_df,
        fallback_used=fallback_used,
    )
