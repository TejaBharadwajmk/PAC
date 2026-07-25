"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm }   from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z }          from "zod";
import { toast }      from "sonner";
import { crimesApi }  from "@/lib/api/crimes.api";
import { KARNATAKA_DISTRICTS, CRIME_TYPE_LABELS } from "@/lib/utils/constants";
import type { CrimeType, CrimeSeverity } from "@/types/api.types";
import { ArrowRight, ArrowLeft, CheckCircle2, FileText, MapPin, Brain } from "lucide-react";
import { cn } from "@/lib/utils/cn";

const crimeCreateSchema = z.object({
  fir_number:       z.string().min(3, "FIR number must be at least 3 characters"),
  crime_type:       z.string().min(1, "Select a crime type"),
  severity:         z.string(),
  district:         z.string().min(1, "Select a district"),
  police_station:   z.string().min(2, "Enter police station name"),
  location_address: z.string().optional(),
  latitude:         z.string().optional().transform((v) => (v ? Number(v) : undefined)),
  longitude:        z.string().optional().transform((v) => (v ? Number(v) : undefined)),
  description:      z.string().optional(),
  mo_text:          z.string().optional(),
  occurred_at:      z.string().min(1, "Occurred date/time is required"),
});

type CrimeForm = z.output<typeof crimeCreateSchema>;

export default function NewCrimePage() {
  const router               = useRouter();
  const [step, setStep]       = useState<number>(1);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { register, handleSubmit, trigger, watch, formState: { errors } } = useForm<any>({
    resolver: zodResolver(crimeCreateSchema),
    defaultValues: {
      severity:    "medium",
      occurred_at: new Date().toISOString().slice(0, 16),
    },
  });

  const formValues = watch();

  const handleNext = async () => {
    let valid = false;
    if (step === 1) {
      valid = await trigger(["fir_number", "crime_type", "severity", "occurred_at"]);
    } else if (step === 2) {
      valid = await trigger(["district", "police_station"]);
    } else if (step === 3) {
      valid = true;
    }
    if (valid) setStep((s) => s + 1);
  };

  const onSubmit = async (data: CrimeForm) => {
    setIsSubmitting(true);
    try {
      const lat = data.latitude !== undefined && !isNaN(data.latitude) ? Number(data.latitude) : undefined;
      const lng = data.longitude !== undefined && !isNaN(data.longitude) ? Number(data.longitude) : undefined;

      const res = await crimesApi.register({
        fir_number:       data.fir_number,
        crime_type:       data.crime_type as CrimeType,
        severity:         data.severity as CrimeSeverity,
        district:         data.district,
        police_station:   data.police_station,
        location_address: data.location_address || undefined,
        latitude:         lat,
        longitude:        lng,
        description:      data.description || undefined,
        mo_text:          data.mo_text || undefined,
        occurred_at:      new Date(data.occurred_at).toISOString(),
      });

      toast.success(`FIR ${res.fir_number} registered successfully!`);
      router.push(`/crimes/${res.id}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to register crime";
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const onInvalid = (fieldErrors: any) => {
    console.error("Form Validation Errors:", fieldErrors);
    const firstErr = Object.values(fieldErrors)[0] as { message?: string } | undefined;
    toast.error(firstErr?.message || "Please fix validation errors before submitting.");
  };

  return (
    <div className="p-6 max-w-3xl mx-auto flex flex-col gap-6">
      {/* Header */}
      <div>
        <h1 className="text-[18px] font-bold text-[#e6edf3]">Register New FIR</h1>
        <p className="text-[13px] text-[#8b949e] mt-0.5">
          Enter First Information Report details. Modus Operandi (MO) features and Crime DNA embeddings are extracted automatically.
        </p>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center justify-between border-b border-[#30363d] pb-4">
        {[
          { num: 1, label: "Basic Info", icon: FileText },
          { num: 2, label: "Location",   icon: MapPin },
          { num: 3, label: "MO Narrative",icon: Brain },
          { num: 4, label: "Review",     icon: CheckCircle2 },
        ].map((s) => {
          const active  = step === s.num;
          const done    = step > s.num;
          return (
            <div key={s.num} className="flex items-center gap-2">
              <div
                className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center font-mono text-[12px] font-bold border",
                  done   ? "bg-[#3fb950]/20 border-[#3fb950] text-[#3fb950]" :
                  active ? "bg-[#1f6feb]/20 border-[#58a6ff] text-[#58a6ff]" :
                           "bg-[#21262d] border-[#30363d] text-[#8b949e]",
                )}
              >
                {done ? <CheckCircle2 size={16} /> : s.num}
              </div>
              <span className={cn("text-[12px] font-semibold hidden md:inline", active ? "text-[#e6edf3]" : "text-[#8b949e]")}>
                {s.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Form Content */}
      <form onSubmit={handleSubmit(onSubmit, onInvalid)} className="pac-card flex flex-col gap-5">
        {/* Step 1: Basic Info */}
        {step === 1 && (
          <div className="flex flex-col gap-4 animate-fade-in">
            <h2 className="text-[14px] font-semibold text-[#e6edf3] flex items-center gap-2">
              <FileText size={16} className="text-[#58a6ff]" />
              Basic Case Info
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-semibold text-[#8b949e]">FIR Number *</label>
                <input
                  type="text"
                  placeholder="e.g. FIR-2026-BLR-0042"
                  {...register("fir_number")}
                  className="bg-[#0d1117] border border-[#30363d] rounded text-[13px] px-3 py-2 text-[#e6edf3] font-mono focus:outline-none focus:border-[#58a6ff]"
                />
                {errors.fir_number?.message ? <p className="text-[11px] text-[#f85149]">{String(errors.fir_number.message)}</p> : null}
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-semibold text-[#8b949e]">Crime Category *</label>
                <select
                  {...register("crime_type")}
                  className="bg-[#0d1117] border border-[#30363d] rounded text-[13px] px-3 py-2 text-[#e6edf3] focus:outline-none focus:border-[#58a6ff]"
                >
                  <option value="">Select category…</option>
                  {Object.entries(CRIME_TYPE_LABELS).map(([k, label]) => (
                    <option key={k} value={k}>{label}</option>
                  ))}
                </select>
                {errors.crime_type?.message ? <p className="text-[11px] text-[#f85149]">{String(errors.crime_type.message)}</p> : null}
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-semibold text-[#8b949e]">Severity Level</label>
                <select
                  {...register("severity")}
                  className="bg-[#0d1117] border border-[#30363d] rounded text-[13px] px-3 py-2 text-[#e6edf3] focus:outline-none focus:border-[#58a6ff]"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-semibold text-[#8b949e]">Date & Time of Occurrence *</label>
                <input
                  type="datetime-local"
                  {...register("occurred_at")}
                  className="bg-[#0d1117] border border-[#30363d] rounded text-[13px] px-3 py-2 text-[#e6edf3] font-mono focus:outline-none focus:border-[#58a6ff]"
                />
                {errors.occurred_at?.message ? <p className="text-[11px] text-[#f85149]">{String(errors.occurred_at.message)}</p> : null}
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Location */}
        {step === 2 && (
          <div className="flex flex-col gap-4 animate-fade-in">
            <h2 className="text-[14px] font-semibold text-[#e6edf3] flex items-center gap-2">
              <MapPin size={16} className="text-[#58a6ff]" />
              Location Details
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-semibold text-[#8b949e]">District *</label>
                <select
                  {...register("district")}
                  className="bg-[#0d1117] border border-[#30363d] rounded text-[13px] px-3 py-2 text-[#e6edf3] focus:outline-none focus:border-[#58a6ff]"
                >
                  <option value="">Select district…</option>
                  {KARNATAKA_DISTRICTS.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
                {errors.district?.message ? <p className="text-[11px] text-[#f85149]">{String(errors.district.message)}</p> : null}
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-semibold text-[#8b949e]">Police Station *</label>
                <input
                  type="text"
                  placeholder="e.g. Indiranagar Police Station"
                  {...register("police_station")}
                  className="bg-[#0d1117] border border-[#30363d] rounded text-[13px] px-3 py-2 text-[#e6edf3] focus:outline-none focus:border-[#58a6ff]"
                />
                {errors.police_station?.message ? <p className="text-[11px] text-[#f85149]">{String(errors.police_station.message)}</p> : null}
              </div>

              <div className="md:col-span-2 flex flex-col gap-1.5">
                <label className="text-[12px] font-semibold text-[#8b949e]">Specific Location / Address</label>
                <input
                  type="text"
                  placeholder="e.g. 100 Feet Road, Near Metro Station"
                  {...register("location_address")}
                  className="bg-[#0d1117] border border-[#30363d] rounded text-[13px] px-3 py-2 text-[#e6edf3] focus:outline-none focus:border-[#58a6ff]"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-semibold text-[#8b949e]">Latitude (Optional)</label>
                <input
                  type="number"
                  step="any"
                  placeholder="e.g. 12.9716"
                  {...register("latitude")}
                  className="bg-[#0d1117] border border-[#30363d] rounded text-[13px] px-3 py-2 text-[#e6edf3] font-mono focus:outline-none focus:border-[#58a6ff]"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-semibold text-[#8b949e]">Longitude (Optional)</label>
                <input
                  type="number"
                  step="any"
                  placeholder="e.g. 77.5946"
                  {...register("longitude")}
                  className="bg-[#0d1117] border border-[#30363d] rounded text-[13px] px-3 py-2 text-[#e6edf3] font-mono focus:outline-none focus:border-[#58a6ff]"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 3: MO Narrative */}
        {step === 3 && (
          <div className="flex flex-col gap-4 animate-fade-in">
            <h2 className="text-[14px] font-semibold text-[#e6edf3] flex items-center gap-2">
              <Brain size={16} className="text-[#bc8cff]" />
              Modus Operandi Narrative (Crime DNA Input)
            </h2>

            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-semibold text-[#8b949e]">Brief Description</label>
                <textarea
                  rows={3}
                  placeholder="Summary of the incident..."
                  {...register("description")}
                  className="bg-[#0d1117] border border-[#30363d] rounded text-[13px] p-3 text-[#e6edf3] focus:outline-none focus:border-[#58a6ff]"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-semibold text-[#e6edf3] flex items-center justify-between">
                  <span>Full MO Narrative (Used for 384-dim Crime DNA Embedding)</span>
                  <span className="text-[11px] text-[#bc8cff] font-normal">Rule-based MO Extraction Engine</span>
                </label>
                <textarea
                  rows={6}
                  placeholder="Describe exact criminal methods, tools used, entry/exit tactics, target types, time patterns, vehicle involved, etc. Detailed narratives produce higher-accuracy similarity matches."
                  {...register("mo_text")}
                  className="bg-[#0d1117] border border-[#30363d] rounded text-[13px] p-3 text-[#e6edf3] focus:outline-none focus:border-[#bc8cff]"
                />
                <p className="text-[11px] text-[#8b949e]">
                  The MO text will be processed by the ML engine to generate vector embeddings automatically in the background.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Review */}
        {step === 4 && (
          <div className="flex flex-col gap-4 animate-fade-in">
            <h2 className="text-[14px] font-semibold text-[#e6edf3] flex items-center gap-2">
              <CheckCircle2 size={16} className="text-[#3fb950]" />
              Review FIR Entry
            </h2>

            <div className="grid grid-cols-2 gap-4 bg-[#0d1117] p-4 rounded border border-[#30363d] text-[13px]">
              <div>
                <p className="text-[11px] text-[#8b949e] uppercase font-mono">FIR Number</p>
                <p className="font-mono text-[#58a6ff] font-semibold">{formValues.fir_number}</p>
              </div>
              <div>
                <p className="text-[11px] text-[#8b949e] uppercase font-mono">Category</p>
                <p className="text-[#e6edf3]">{CRIME_TYPE_LABELS[formValues.crime_type]}</p>
              </div>
              <div>
                <p className="text-[11px] text-[#8b949e] uppercase font-mono">District & Station</p>
                <p className="text-[#e6edf3]">{formValues.district} · {formValues.police_station}</p>
              </div>
              <div>
                <p className="text-[11px] text-[#8b949e] uppercase font-mono">Severity</p>
                <p className="text-[#e6edf3] capitalize">{formValues.severity}</p>
              </div>
            </div>

            {formValues.mo_text && (
              <div className="bg-[#0d1117] p-4 rounded border border-[#30363d]">
                <p className="text-[11px] text-[#8b949e] uppercase font-mono mb-1">MO Narrative Preview</p>
                <p className="text-[12px] text-[#c9d1d9] italic">{formValues.mo_text}</p>
              </div>
            )}
          </div>
        )}

        {/* Buttons */}
        <div className="flex items-center justify-between border-t border-[#30363d] pt-4 mt-2">
          {step > 1 ? (
            <button
              type="button"
              onClick={() => setStep((s) => s - 1)}
              className="px-4 py-2 rounded border border-[#30363d] text-[#e6edf3] text-[13px] hover:bg-[#21262d] flex items-center gap-1.5"
            >
              <ArrowLeft size={14} /> Back
            </button>
          ) : <div />}

          {step < 4 ? (
            <button
              type="button"
              onClick={handleNext}
              className="px-5 py-2 rounded bg-[#1f6feb] hover:bg-[#388bfd] text-white text-[13px] font-semibold flex items-center gap-1.5"
            >
              Next <ArrowRight size={14} />
            </button>
          ) : (
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-6 py-2 rounded bg-[#3fb950] hover:bg-[#2ea043] text-white text-[13px] font-bold flex items-center gap-2 disabled:opacity-50 cursor-pointer"
            >
              {isSubmitting ? "Submitting FIR…" : "Submit & Register FIR"}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
