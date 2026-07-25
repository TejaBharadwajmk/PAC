import Link from "next/link";
import { ShieldOff } from "lucide-react";

export default function UnauthorizedPage() {
  return (
    <div className="min-h-screen bg-[#0d1117] flex items-center justify-center p-4">
      <div className="text-center max-w-sm">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-[rgba(248,81,73,0.15)] border border-[rgba(248,81,73,0.4)] mb-6">
          <ShieldOff size={28} className="text-[#f85149]" />
        </div>
        <h1 className="text-xl font-bold text-[#e6edf3] mb-2">Access Denied</h1>
        <p className="text-[13px] text-[#8b949e] mb-6 leading-relaxed">
          Your role does not have permission to access this module. Contact your supervisor or system administrator.
        </p>
        <Link
          href="/"
          className="inline-flex items-center px-4 py-2 bg-[#1f6feb] hover:bg-[#388bfd] text-white text-[13px] font-semibold rounded transition-colors"
        >
          Return to Dashboard
        </Link>
      </div>
    </div>
  );
}
