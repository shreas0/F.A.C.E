#pragma once

bool wifi_manager_init();
bool wifi_manager_ensure_time_synced();
bool wifi_manager_connect();
void wifi_manager_stop();
bool wifi_manager_recovery_requested();
bool wifi_manager_take_frame_request();
bool wifi_manager_test_mode_active();
