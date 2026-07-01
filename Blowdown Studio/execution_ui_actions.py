from __future__ import annotations


def run_psv_ui_flow_with_feedback(
    app,
    *,
    converter,
    collect_payload_fn,
    get_active_vendor_catalog_fn,
    execute_workflow_fn,
    apply_result_fn,
    load_api526_data,
    load_api6d_data,
    set_status_text_fn,
    refresh_ui_fn,
    showerror_fn,
):
    try:
        app.last_psv_report_bundle = None
        set_status_text_fn("Hesaplanıyor... Lütfen bekleyin.\n")
        refresh_ui_fn()
        payload = collect_payload_fn(app, converter=converter)
        active_vendor_catalog = get_active_vendor_catalog_fn()
        workflow = execute_workflow_fn(
            inputs=payload["inputs"],
            service_type=payload["service_type"],
            valve_type=payload["valve_type"],
            valve_count=payload["valve_count"],
            rupture_disk=payload["rupture_disk"],
            flow_unit=payload["flow_unit"],
            flow_value=payload["flow_value"],
            normalized_composition=payload["normalized_composition"],
            active_vendor_catalog=active_vendor_catalog,
            load_api526_data=load_api526_data,
            load_api6d_data=load_api6d_data,
            converter=converter,
        )
        return apply_result_fn(app, workflow, app.vendor_catalog_path)
    except Exception as exc:
        app.last_psv_report_bundle = None
        showerror_fn("Hata", f"Hesaplama hatası:\n{str(exc)}")
        set_status_text_fn(f"HATA: {exc}\n")
        return None


def run_blowdown_ui_flow_with_feedback(
    *,
    user_inputs,
    native_engine_name,
    execute_flow_fn,
    update_progress_ui,
    abort_flag,
    load_api526_data,
    load_api6d_data,
    size_area_fn,
    select_standard_valve_fn,
    run_engine_fn,
    build_report_fn,
    logger,
    schedule_ui_fn,
    update_results_fn,
    plot_results_fn,
    showerror_fn,
    showwarning_fn,
    finalize_run_button_fn,
    finalize_abort_button_fn,
    store_report_bundle_fn=lambda bundle: None,
):
    try:
        logger.info("Simülasyon motoru başlatılıyor...")
        result = execute_flow_fn(
            user_inputs=user_inputs,
            native_engine_name=native_engine_name,
            update_progress_ui=update_progress_ui,
            abort_flag=abort_flag,
            load_api526_data=load_api526_data,
            load_api6d_data=load_api6d_data,
            size_area_fn=size_area_fn,
            select_standard_valve_fn=select_standard_valve_fn,
            run_engine_fn=run_engine_fn,
            build_report_fn=build_report_fn,
        )

        if result.status == "aborted":
            logger.warning("Simülasyon kullanıcı tarafından durduruldu.")
            return result

        if result.fallback_used:
            logger.warning("Gerekli alanı karşılayan standart vana bulunamadı. En büyük standart vana seçildi.")
            schedule_ui_fn(
                0,
                lambda: showwarning_fn(
                    "Vana Uyarısı",
                    "Gerekli alanı karşılayan standart vana bulunamadı.\n"
                    "En büyük standart vana seçildi.\n"
                    "Çoklu vana kullanımını değerlendirin.",
                ),
            )

        logger.info("Analiz başarıyla tamamlandı.")
        if result.workflow_result and result.workflow_result["verdict"] == "FAIL":
            logger.error(
                "KRİTİK: Hedef süre aşıldı! (%.1fs > %.1fs)",
                result.workflow_result["sim_time_s"],
                result.workflow_result["target_time_s"],
            )
            schedule_ui_fn(
                0,
                lambda: showerror_fn(
                    "Analiz Sonucu: BAŞARISIZ",
                    f"Hedef süre aşıldı!\n\n"
                    f"Simülasyon: {result.workflow_result['sim_time_s']:.1f} s\n"
                    f"Hedef: {result.workflow_result['target_time_s']:.0f} s\n\n"
                    "Vana alanını artırmayı veya çoklu vana kullanmayı değerlendirin.",
                ),
            )

        schedule_ui_fn(0, store_report_bundle_fn, result.workflow_result.get("report_bundle"))
        schedule_ui_fn(0, update_results_fn, result.workflow_result["report_text"])
        schedule_ui_fn(0, plot_results_fn, result.sim_df, result.workflow_result["screening_inputs"], result.selected_valve)
        return result
    except Exception as exc:
        logger.exception("Hesaplama sırasında beklenmedik hata oluştu.")
        schedule_ui_fn(0, lambda e=exc: showerror_fn("Hata", f"Hesaplama hatası: {str(e)}"))
        return None
    finally:
        schedule_ui_fn(0, finalize_run_button_fn)
        schedule_ui_fn(0, finalize_abort_button_fn)
