from __future__ import annotations

import threading


def dispatch_run(mode_text: str, *, blowdown_fn, psv_fn):
    if "Blowdown" in mode_text:
        return blowdown_fn()
    return psv_fn()


def start_blowdown_thread(
    app,
    *,
    collect_inputs_fn,
    run_logic_target,
    logger,
    showerror_fn,
    thread_factory=threading.Thread,
):
    try:
        app.user_inputs = collect_inputs_fn()
        app.btn_run["state"] = "disabled"
        app.btn_abort["state"] = "normal"
        app.abort_flag.clear()
        logger.info(
            "YENİ ANALİZ BAŞLATILDI: Vana Tipi=%s, Basınç=%.1f bar",
            app.user_inputs["valve_type"],
            app.user_inputs["p0_pa"] / 1e5,
        )
        worker = thread_factory(target=run_logic_target, daemon=True)
        worker.start()
        return worker
    except Exception as exc:
        app.btn_run["state"] = "normal"
        app.btn_abort["state"] = "disabled"
        logger.error("Giriş hatası: %s", exc)
        showerror_fn("Hata", str(exc))
        return None
