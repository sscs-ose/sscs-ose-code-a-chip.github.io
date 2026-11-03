/* SPDX-License-Identifier: MIT
 * HuLLCirq development_assistant implementation.
 * Read-only callback recorder; no signal assignments or simulator modifications.
 * Global sequence is callback observation order, NOT a scheduler delta/region ID.
 */
#define _GNU_SOURCE
#include <vpi_user.h>
#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>
#include <stdarg.h>
#include <string.h>
#include <ctype.h>

#ifndef HULLCIRQ_MAX_EVENTS
#define HULLCIRQ_MAX_EVENTS UINT64_C(20000000)
#endif
#ifndef HULLCIRQ_MAX_BYTES
#define HULLCIRQ_MAX_BYTES UINT64_C(1073741824)
#endif
#define MAX_SIGNALS 12000
#define MAX_WIDTH 1024
#define MAX_PATH 1024

typedef struct {
    unsigned id, width;
    char *path, *role, *resolved_path;
    int object_type;
    vpiHandle object, callback;
    uint64_t initial_count, change_count, settled_count;
} signal_t;

static signal_t signals[MAX_SIGNALS];
static unsigned signal_count, resolved_count, errors;
static uint64_t sequence, events_written, initial_events, change_callbacks;
static uint64_t settled_events, dropped_events, output_bytes;
static FILE *events;
static int disabled, started, settled_seen, end_seen, precision;
static const char *last_error = "none";

static uint64_t now_ps(void) {
    s_vpi_time time;
    memset(&time, 0, sizeof(time));
    time.type = vpiSimTime;
    vpi_get_time(0, &time);
    return ((uint64_t)time.high << 32) | time.low;
}

static void error(const char *code) {
    ++errors;
    last_error = code;
    vpi_printf("HULLCIRQ_EVENT_CAPTURE_ERROR %s\n", code);
}

static int emit(const char *format, ...) {
    char row[4096];
    va_list args;
    if (!events || disabled) return 0;
    va_start(args, format);
    int size = vsnprintf(row, sizeof(row), format, args);
    va_end(args);
    if (size < 0 || (size_t)size >= sizeof(row)) {
        error("row_overflow"); disabled = 1; return 0;
    }
    if (output_bytes + (uint64_t)size > HULLCIRQ_MAX_BYTES) {
        error("byte_limit"); disabled = 1; return 0;
    }
    if (fwrite(row, 1, (size_t)size, events) != (size_t)size) {
        error("write_failed"); disabled = 1; return 0;
    }
    output_bytes += (uint64_t)size;
    return 1;
}

static int safe_text(const char *text) {
    if (!text || !*text) return 0;
    for (; *text; ++text) if ((unsigned char)*text < 32 || (unsigned char)*text > 126) return 0;
    return 1;
}

static int role_valid(const char *text) {
    if (!safe_text(text)) return 0;
    for (; *text; ++text) if (!isalnum((unsigned char)*text) && *text != '_') return 0;
    return 1;
}

static int unsigned_value(const char *text, unsigned *value) {
    char *end;
    if (!text || !*text || *text < '0' || *text > '9') return 0;
    unsigned long number = strtoul(text, &end, 10);
    if (*end || number > 2147483647UL) return 0;
    *value = (unsigned)number;
    return 1;
}

static void event(signal_t *signal, const char *kind, const s_vpi_value *supplied) {
    s_vpi_value local;
    const s_vpi_value *value = supplied;
    if (disabled) { ++dropped_events; return; }
    if (events_written >= HULLCIRQ_MAX_EVENTS) {
        error("event_limit"); disabled = 1; ++dropped_events; return;
    }
    if (!value) {
        memset(&local, 0, sizeof(local)); local.format = vpiBinStrVal;
        vpi_get_value(signal->object, &local); value = &local;
    }
    if (value->format != vpiBinStrVal || !value->value.str || strlen(value->value.str) != signal->width) {
        error("invalid_binary_value"); disabled = 1; ++dropped_events; return;
    }
    char binary[MAX_WIDTH + 1];
    unsigned i;
    for (i = 0; i < signal->width; ++i) {
        char digit = (char)tolower((unsigned char)value->value.str[i]);
        if (digit != '0' && digit != '1' && digit != 'x' && digit != 'z') {
            error("invalid_four_state_digit"); disabled = 1; ++dropped_events; return;
        }
        binary[i] = digit;
    }
    binary[signal->width] = 0;
    if (!emit("EVENT\t%" PRIu64 "\t%" PRIu64 "\t%u\t%s\t%s\n",
        sequence + 1, now_ps(), signal->id, kind, binary)) { ++dropped_events; return; }
    ++sequence; ++events_written;
    if (!strcmp(kind, "initial")) { ++initial_events; ++signal->initial_count; }
    else if (!strcmp(kind, "settled")) { ++settled_events; ++signal->settled_count; }
    else { ++change_callbacks; ++signal->change_count; }
}

static PLI_INT32 changed(p_cb_data cause) {
    event((signal_t *)cause->user_data, "change", cause->value);
    return 0;
}

static PLI_INT32 settled(p_cb_data cause) {
    (void)cause;
    if (now_ps() != 0) error("settled_not_time_zero");
    settled_seen = 1;
    unsigned i;
    for (i = 0; i < signal_count; ++i) event(&signals[i], "settled", 0);
    if (events && fflush(events)) { error("settled_flush_failed"); disabled = 1; }
    return 0;
}

static int load_manifest(void) {
    s_vpi_vlog_info info;
    const char *manifest = 0;
    const char *prefix = "+hullcirq_event_manifest=";
    if (!vpi_get_vlog_info(&info)) { error("arguments_unavailable"); return 0; }
    int i;
    for (i = 0; i < info.argc; ++i) if (!strncmp(info.argv[i], prefix, strlen(prefix))) {
        if (manifest) { error("duplicate_manifest_argument"); return 0; }
        manifest = info.argv[i] + strlen(prefix);
    }
    if (!manifest || strcmp(manifest, "event-signal-manifest.tsv")) { error("fixed_manifest_required"); return 0; }
    FILE *input = fopen(manifest, "r");
    if (!input) { error("manifest_missing"); return 0; }
    char line[4096];
    if (!fgets(line, sizeof(line), input) || strcmp(line, "HULLCIRQ_EVENT_MANIFEST_V1\n")) {
        error("manifest_header"); fclose(input); return 0;
    }
    while (fgets(line, sizeof(line), input)) {
        size_t size = strlen(line);
        if (!size || line[size - 1] != '\n' || signal_count == MAX_SIGNALS) {
            error("manifest_limit_or_incomplete_row"); fclose(input); return 0;
        }
        line[size - 1] = 0;
        char *fields[4]; fields[0] = line;
        for (i = 1; i < 4; ++i) {
            char *tab = strchr(fields[i - 1], '\t');
            if (!tab) { error("manifest_columns"); fclose(input); return 0; }
            *tab = 0; fields[i] = tab + 1;
        }
        unsigned id, width;
        if (strchr(fields[3], '\t') || !unsigned_value(fields[0], &id) || id != signal_count + 1
            || !unsigned_value(fields[2], &width) || !width || width > MAX_WIDTH
            || strlen(fields[1]) > MAX_PATH || !safe_text(fields[1]) || !role_valid(fields[3])) {
            error("manifest_value"); fclose(input); return 0;
        }
        unsigned j;
        for (j = 0; j < signal_count; ++j) if (!strcmp(signals[j].path, fields[1])) {
            error("duplicate_signal_path"); fclose(input); return 0;
        }
        signal_t *signal = &signals[signal_count++];
        signal->id = id; signal->width = width;
        signal->path = strdup(fields[1]); signal->role = strdup(fields[3]);
        if (!signal->path || !signal->role) { error("allocation_failed"); fclose(input); return 0; }
    }
    int ok = !ferror(input) && signal_count > 0;
    if (!ok) error("manifest_empty_or_read_error");
    if (fclose(input)) { error("manifest_close_failed"); ok = 0; }
    return ok;
}

static PLI_INT32 start(p_cb_data cause) {
    (void)cause;
    precision = vpi_get(vpiTimePrecision, 0);
    if (precision != -12) { error("precision_not_picoseconds"); return 0; }
    if (!load_manifest()) return 0;
    events = fopen("hullcirq-events.tsv", "wx");
    if (!events) { error("output_exists_or_unwritable"); return 0; }
    setvbuf(events, 0, _IOFBF, 65536);
    emit("HULLCIRQ_EVENTS_V1\nMETA\ttime_precision\t-12\nMETA\tdelta_identity\tunavailable\n");
    unsigned i;
    for (i = 0; i < signal_count; ++i) {
        signal_t *signal = &signals[i];
        signal->object = vpi_handle_by_name(signal->path, 0);
        if (!signal->object || vpi_get(vpiSize, signal->object) != (int)signal->width) {
            error("signal_missing_or_width_conflict"); disabled = 1; return 0;
        }
        signal->object_type = vpi_get(vpiType, signal->object);
        if (signal->object_type != vpiNet && signal->object_type != vpiReg
            && signal->object_type != vpiNetBit && signal->object_type != vpiRegBit) {
            error("signal_object_type_unsupported"); disabled = 1; return 0;
        }
        const char *resolved = vpi_get_str(vpiFullName, signal->object);
        signal->resolved_path = resolved ? strdup(resolved) : 0;
        if (!signal->resolved_path || !safe_text(signal->resolved_path)) {
            error("resolved_path_unavailable"); disabled = 1; return 0;
        }
        s_vpi_value value; s_vpi_time time; s_cb_data callback;
        memset(&value, 0, sizeof(value)); memset(&time, 0, sizeof(time)); memset(&callback, 0, sizeof(callback));
        value.format = vpiBinStrVal; time.type = vpiSimTime;
        callback.reason = cbValueChange; callback.cb_rtn = changed; callback.obj = signal->object;
        callback.time = &time; callback.value = &value; callback.user_data = (PLI_BYTE8 *)signal;
        signal->callback = vpi_register_cb(&callback);
        if (!signal->callback) { error("callback_registration_failed"); disabled = 1; return 0; }
        ++resolved_count;
        emit("SIGNAL\t%u\t%s\t%u\t%s\n", signal->id, signal->path, signal->width, signal->role);
    }
    started = 1;
    for (i = 0; i < signal_count; ++i) event(&signals[i], "initial", 0);
    s_cb_data callback; s_vpi_time time;
    memset(&callback, 0, sizeof(callback)); memset(&time, 0, sizeof(time));
    time.type = vpiSimTime;
    callback.reason = cbReadOnlySynch; callback.cb_rtn = settled; callback.time = &time;
    if (!vpi_register_cb(&callback)) { error("settled_callback_registration_failed"); disabled = 1; }
    return 0;
}

static void json_string(FILE *file, const char *text) {
    fputc('"', file);
    for (; text && *text; ++text) {
        if (*text == '"' || *text == '\\') fputc('\\', file);
        fputc(*text, file);
    }
    fputc('"', file);
}

static PLI_INT32 finish(p_cb_data cause) {
    (void)cause;
    end_seen = 1;
    unsigned i;
    if (events) {
        for (i = 0; i < signal_count; ++i) emit("COUNTS\t%u\t%" PRIu64 "\t%" PRIu64 "\t%" PRIu64 "\n",
            signals[i].id, signals[i].initial_count, signals[i].change_count, signals[i].settled_count);
        emit("END\t%" PRIu64 "\t%" PRIu64 "\t%u\t%" PRIu64 "\t%u\t%d\n",
            sequence, now_ps(), signal_count, events_written, errors,
            started && settled_seen && !disabled && !errors && !dropped_events);
    }
    int flush_complete = 0;
    if (events) {
        int flushed = fflush(events), closed = fclose(events); events = 0;
        flush_complete = !flushed && !closed;
        if (!flush_complete) error("final_flush_or_close_failed");
    }
    FILE *summary = fopen("hullcirq-events-summary.json", "wx");
    if (!summary) { error("summary_exists_or_unwritable"); return 0; }
    int complete = started && settled_seen && !disabled && !errors && !dropped_events && flush_complete;
    fprintf(summary, "{\n\"schema_version\":\"hullcirq-event-capture-summary-v1\",\n"
        "\"time_precision\":%d,\"delta_identity\":\"unavailable\",\"ordering\":\"callback_invocation_order\",\n"
        "\"initial_scope\":\"cbStartOfSimulation_before_initial_threads\",\"settled_scope\":\"time_zero_cbReadOnlySynch\",\n"
        "\"manifest_signal_count\":%u,\"resolved_signal_count\":%u,\"events_written\":%" PRIu64 ",\n"
        "\"initial_events\":%" PRIu64 ",\"change_callbacks\":%" PRIu64 ",\"settled_events\":%" PRIu64 ",\n"
        "\"last_sequence\":%" PRIu64 ",\"end_time_ps\":%" PRIu64 ",\"dropped_events\":%" PRIu64 ",\n"
        "\"output_bytes\":%" PRIu64 ",\"max_events\":%" PRIu64 ",\"max_bytes\":%" PRIu64 ",\"error_count\":%u,\n"
        "\"flush_complete\":%s,\"capture_complete\":%s,\"end_callback_seen\":%s,\"last_error\":\"%s\",\n\"signals\":[\n",
        precision, signal_count, resolved_count, events_written, initial_events, change_callbacks, settled_events,
        sequence, now_ps(), dropped_events, output_bytes, HULLCIRQ_MAX_EVENTS, HULLCIRQ_MAX_BYTES, errors,
        flush_complete ? "true" : "false", complete ? "true" : "false", end_seen ? "true" : "false", last_error);
    for (i = 0; i < signal_count; ++i) {
        signal_t *signal = &signals[i];
        fprintf(summary, "%s{\"id\":%u,\"width\":%u,\"path\":", i ? ",\n" : "", signal->id, signal->width);
        json_string(summary, signal->path); fprintf(summary, ",\"resolved_path\":"); json_string(summary, signal->resolved_path);
        fprintf(summary, ",\"role\":"); json_string(summary, signal->role);
        fprintf(summary, ",\"object_type\":%d,\"initial_count\":%" PRIu64 ",\"change_count\":%" PRIu64 ",\"settled_count\":%" PRIu64 "}",
            signal->object_type, signal->initial_count, signal->change_count, signal->settled_count);
    }
    fprintf(summary, "\n]}\n");
    if (fflush(summary) || ferror(summary)) error("summary_write_failed");
    if (fclose(summary)) error("summary_close_failed");
    vpi_printf("HULLCIRQ_EVENT_CAPTURE_END complete=%d events=%" PRIu64 " errors=%u\n", complete, events_written, errors);
    return 0;
}

static void register_capture(void) {
    s_cb_data callback;
    memset(&callback, 0, sizeof(callback)); callback.reason = cbStartOfSimulation; callback.cb_rtn = start;
    vpi_register_cb(&callback);
    memset(&callback, 0, sizeof(callback)); callback.reason = cbEndOfSimulation; callback.cb_rtn = finish;
    vpi_register_cb(&callback);
}

void (*vlog_startup_routines[])(void) = { register_capture, 0 };
