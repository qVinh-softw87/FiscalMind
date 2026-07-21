import React, { useState } from 'react';
import { api } from '../services/api';
import { Sparkles, Mail, Lock, User, ArrowRight, AlertCircle, Info } from 'lucide-react';

interface AuthScreenProps {
  onAuthSuccess: () => void;
}

export default function AuthScreen({ onAuthSuccess }: AuthScreenProps) {
  const [isLogin, setIsLogin] = useState<boolean>(true);
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [fullName, setFullName] = useState<string>('');
  
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      if (isLogin) {
        // Handle Login
        await api.login({ email, password });
        onAuthSuccess();
      } else {
        // Handle Register
        await api.register({ email, password, full_name: fullName });
        setSuccessMsg('Đăng ký tài khoản thành công! Vui lòng chuyển sang Đăng nhập.');
        setIsLogin(true);
        setPassword('');
      }
    } catch (err: any) {
      setError(err.message || 'Đã xảy ra lỗi không mong muốn.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-[#0B0D17] flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background Decorative Gradients */}
      <div className="absolute top-[-20%] left-[-20%] w-[60%] h-[60%] rounded-full bg-violet-600/10 blur-[150px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-20%] w-[60%] h-[60%] rounded-full bg-blue-600/10 blur-[150px] pointer-events-none" />

      {/* Auth Card */}
      <div className="w-full max-w-md bg-[#131520]/80 backdrop-blur-md border border-white/5 rounded-3xl p-8 md:p-10 shadow-2xl relative z-10">
        
        {/* Brand Header */}
        <div className="flex flex-col items-center text-center mb-8">
          <div className="bg-gradient-to-tr from-violet-600 to-indigo-600 p-3 rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-600/20 mb-3">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-display font-extrabold text-white tracking-tight">FiscalMind AI</h1>
          <p className="text-xs text-white/50 font-medium uppercase tracking-wider mt-1">Cố vấn CFO Tài chính Doanh nghiệp</p>
        </div>

        {/* Action Title */}
        <div className="mb-6">
          <h2 className="text-lg font-bold text-white">
            {isLogin ? 'Đăng nhập vào hệ thống' : 'Đăng ký tài khoản mới'}
          </h2>
          <p className="text-xs text-white/60 mt-1">
            {isLogin ? 'Nhập thông tin tài khoản để truy cập dashboard phân tích' : 'Điền đầy đủ thông tin để bắt đầu trải nghiệm trợ lý AI'}
          </p>
        </div>

        {/* Messages */}
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-950/30 border border-red-500/20 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <div className="text-xs font-medium text-red-200 leading-relaxed">{error}</div>
          </div>
        )}

        {successMsg && (
          <div className="mb-6 p-4 rounded-xl bg-emerald-950/30 border border-emerald-500/20 flex items-start gap-3">
            <Info className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            <div className="text-xs font-medium text-emerald-200 leading-relaxed">{successMsg}</div>
          </div>
        )}

        {/* Auth Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          
          {/* Full Name (Register Only) */}
          {!isLogin && (
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-white/70 block">Họ và tên</label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-white/40">
                  <User className="w-4 h-4" />
                </span>
                <input
                  type="text"
                  required
                  placeholder="Nguyễn Văn A"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl py-2.5 pl-10 pr-4 text-sm text-white placeholder-white/30 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>
            </div>
          )}

          {/* Email */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-white/70 block">Địa chỉ Email</label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-white/40">
                <Mail className="w-4 h-4" />
              </span>
              <input
                type="email"
                required
                placeholder="name@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl py-2.5 pl-10 pr-4 text-sm text-white placeholder-white/30 focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>
          </div>

          {/* Password */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-white/70 block">Mật khẩu</label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-white/40">
                <Lock className="w-4 h-4" />
              </span>
              <input
                type="password"
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl py-2.5 pl-10 pr-4 text-sm text-white placeholder-white/30 focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>

            {/* Password Hint for Registration */}
            {!isLogin && (
              <p className="text-[10px] text-white/40 leading-normal pt-1">
                * Yêu cầu: tối thiểu 8 ký tự, gồm ít nhất 1 chữ hoa, 1 chữ thường và 1 số.
              </p>
            )}
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 disabled:opacity-50 text-white font-semibold py-3 px-4 rounded-xl text-sm transition-all duration-200 flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/10 active:scale-98 mt-2"
          >
            {loading ? (
              <span className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                <span>{isLogin ? 'Đăng nhập' : 'Tạo tài khoản'}</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Toggle Switch */}
        <div className="text-center mt-6 text-xs text-white/40 font-medium">
          {isLogin ? (
            <>
              Chưa có tài khoản?{' '}
              <button
                onClick={() => {
                  setIsLogin(false);
                  setError(null);
                }}
                className="text-indigo-400 hover:underline font-bold"
              >
                Đăng ký ngay
              </button>
            </>
          ) : (
            <>
              Đã có tài khoản?{' '}
              <button
                onClick={() => {
                  setIsLogin(true);
                  setError(null);
                }}
                className="text-indigo-400 hover:underline font-bold"
              >
                Quay lại đăng nhập
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
