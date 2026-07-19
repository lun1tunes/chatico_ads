import { useState, useRef, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { PLATFORMS, useAppStore } from '../../store/useAppStore';
import { MOCK_CAMPAIGNS } from '../../data/mockCampaigns';
import Logo from '../ui/Logo';
import CampaignNavItem from './CampaignNavItem';

const PLATFORMS_DETAILS = {
  [PLATFORMS.META]: {
    label: 'Facebook / Instagram',
    icon: (
      <svg className="h-5 w-5 shrink-0 text-[#1877F2]" fill="currentColor" viewBox="0 0 24 24">
        <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
      </svg>
    ),
    active: true,
  },
  [PLATFORMS.GOOGLE]: {
    label: 'Google Ads',
    icon: (
      <svg className="h-5 w-5 shrink-0 text-[#EA4335]" fill="currentColor" viewBox="0 0 24 24">
        <path d="M12.24 10.285V14.4h6.887c-.648 2.41-2.519 4.114-6.887 4.114-4.694 0-8.511-3.817-8.511-8.514 0-4.697 3.817-8.514 8.511-8.514 2.03 0 3.887.77 5.316 2.034l3.146-3.146C18.187 1.95 15.42 1 12.24 1 5.48 1 0 6.48 0 13.24s5.48 12.24 12.24 12.24c6.76 0 12.24-5.48 12.24-12.24 0-.82-.07-1.63-.21-2.415H12.24z" />
      </svg>
    ),
    active: false,
  },
  [PLATFORMS.TIKTOK]: {
    label: 'TikTok Ads',
    icon: (
      <svg className="h-5 w-5 shrink-0 text-black" fill="currentColor" viewBox="0 0 24 24">
        <path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.02 1.59 4.18 1.02 1.22 2.49 2.01 4.07 2.23v3.8c-1.42-.17-2.78-.74-3.91-1.58-.69-.51-1.27-1.15-1.72-1.89-.04 2.87-.02 5.74-.03 8.61-.05 1.56-.47 3.12-1.25 4.45-1.2 2.07-3.37 3.51-5.75 3.73-2.14.2-4.36-.37-5.99-1.77-1.83-1.56-2.73-4.01-2.31-6.38.35-2.02 1.63-3.86 3.48-4.78 1.48-.74 3.17-.92 4.78-.52v3.91c-1.11-.32-2.34-.1-3.26.58-.93.68-1.43 1.83-1.32 2.99.09 1.02.73 1.96 1.67 2.33.91.37 1.96.24 2.76-.35.63-.47.98-1.22 1.01-2.01.03-3.24.01-6.48.02-9.72z" />
      </svg>
    ),
    active: false,
  },
};

export default function Sidebar() {
  const location = useLocation();
  const selectedPlatform = useAppStore((s) => s.selectedPlatform);
  const setPlatform = useAppStore((s) => s.setPlatform);
  const isCollapsed = useAppStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);

  const [isCampaignsOpen, setIsCampaignsOpen] = useState(true);
  const [isPlatformDropdownOpen, setIsPlatformDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  const isMeta = selectedPlatform === PLATFORMS.META;
  const isCampaignActive = location.pathname.startsWith('/campaigns/');
  const currentPlatform = PLATFORMS_DETAILS[selectedPlatform];

  // Закрываем дропдаун при клике вне его области
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsPlatformDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <aside
      className={`relative flex h-full shrink-0 flex-col border-r border-outline bg-white transition-all duration-300 ease-in-out ${
        isCollapsed ? 'w-20' : 'w-72'
      }`}
    >
      {/* Кнопка сворачивания/развертывания на границе */}
      <button
        type="button"
        onClick={toggleSidebar}
        className="absolute -right-3.5 top-6 z-50 flex h-7 w-7 items-center justify-center rounded-full border border-outline bg-white text-gray-400 shadow-md transition-transform duration-200 hover:scale-110 hover:text-gray-700"
        aria-label={isCollapsed ? 'Развернуть меню' : 'Свернуть меню'}
      >
        <svg
          className={`h-4 w-4 transition-transform duration-300 ${
            isCollapsed ? 'rotate-180' : ''
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2.5}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      {/* 1. Шапка (Header) на чистом белом фоне */}
      <div className="flex h-20 shrink-0 flex-col justify-center bg-white px-6 border-b border-outline">
        <div className="flex items-center gap-3">
          {/* Векторный логотип Chatico ADS на чистом белом фоне */}
          <Logo height={24} to="/" />
        </div>
      </div>

      {/* 2. Выбор рекламного инструмента */}
      <div className="shrink-0 border-b border-outline px-4 py-4" ref={dropdownRef}>
        {isCollapsed ? (
          /* В свернутом виде: Иконка с поповером */
          <div className="group relative flex justify-center">
            <button
              type="button"
              onClick={toggleSidebar}
              className="flex h-10 w-10 items-center justify-center rounded-xl bg-gray-50 border border-outline transition-all duration-150 hover:bg-gray-100"
            >
              {currentPlatform.icon}
            </button>
            {/* Поповер выбора платформы */}
            <div className="absolute left-full top-0 z-50 ml-3 hidden w-64 rounded-2xl border border-outline bg-white p-2 shadow-lg group-hover:block">
              <p className="mb-2 px-2 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                Рекламный инструмент
              </p>
              <ul className="space-y-1">
                {Object.entries(PLATFORMS_DETAILS).map(([key, value]) => (
                  <li key={key}>
                    <button
                      type="button"
                      disabled={!value.active}
                      onClick={() => {
                        setPlatform(key);
                        setIsPlatformDropdownOpen(false);
                      }}
                      className={`flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left text-xs font-semibold transition-colors ${
                        selectedPlatform === key
                          ? 'bg-[#5E44EB]/10 text-[#5E44EB]'
                          : value.active
                          ? 'text-gray-700 hover:bg-gray-50'
                          : 'text-gray-400 opacity-50 cursor-not-allowed'
                      }`}
                    >
                      {value.icon}
                      <span className="flex-1 truncate">{value.label}</span>
                      {!value.active && (
                        <span className="rounded-full bg-gray-100 px-1.5 py-0.5 text-[8px] font-semibold text-gray-500">
                          скоро
                        </span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : (
          /* В развернутом виде: Dropdown */
          <div className="relative">
            <p className="mb-1.5 px-1 text-[10px] font-bold uppercase tracking-wider text-gray-400">
              Рекламный инструмент
            </p>
            <button
              type="button"
              onClick={() => setIsPlatformDropdownOpen(!isPlatformDropdownOpen)}
              className="flex w-full items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3 text-left text-sm font-semibold text-gray-700 shadow-sm transition-all duration-150 hover:bg-gray-50"
            >
              {currentPlatform.icon}
              <span className="flex-1 truncate">{currentPlatform.label}</span>
              <svg
                className={`h-4 w-4 text-gray-400 transition-transform duration-200 ${
                  isPlatformDropdownOpen ? 'rotate-180' : ''
                }`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2.5}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {/* Выпадающий список платформ */}
            {isPlatformDropdownOpen && (
              <div className="absolute left-0 right-0 z-50 mt-1 rounded-2xl border border-outline bg-white p-1.5 shadow-lg">
                <ul className="space-y-0.5">
                  {Object.entries(PLATFORMS_DETAILS).map(([key, value]) => (
                    <li key={key}>
                      <button
                        type="button"
                        disabled={!value.active}
                        onClick={() => {
                          setPlatform(key);
                          setIsPlatformDropdownOpen(false);
                        }}
                        className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors ${
                          selectedPlatform === key
                            ? 'bg-[#5E44EB]/10 text-[#5E44EB] font-semibold'
                            : value.active
                            ? 'text-gray-700 hover:bg-gray-50'
                            : 'text-gray-400 opacity-50 cursor-not-allowed'
                        }`}
                      >
                        {value.icon}
                        <span className="flex-1 truncate">{value.label}</span>
                        {!value.active && (
                          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[9px] font-semibold text-gray-500">
                            скоро
                          </span>
                        )}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Навигация */}
      <div className="flex min-h-0 flex-1 flex-col gap-4 px-3 py-4 overflow-y-auto">
        {/* Обзор аккаунта */}
        <ul className="space-y-1">
          <li>
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                [
                  'group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-semibold transition-all duration-150',
                  isActive
                    ? 'bg-[#5E44EB] text-white shadow-sm font-bold'
                    : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900',
                ].join(' ')
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <div className="absolute left-0 top-2.5 bottom-2.5 w-[4px] rounded-r-md bg-[#c2f913]" />
                  )}
                  <svg
                    className="h-5 w-5 shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
                    />
                  </svg>
                  {!isCollapsed && <span>Обзор аккаунта</span>}

                  {isCollapsed && (
                    <div className="absolute left-full top-1/2 z-50 ml-3 -translate-y-1/2 rounded-md bg-on-surface px-2.5 py-1.5 text-xs font-semibold text-surface opacity-0 shadow-md transition-opacity group-hover:opacity-100 pointer-events-none whitespace-nowrap">
                      Обзор аккаунта
                    </div>
                  )}
                </>
              )}
            </NavLink>
          </li>
        </ul>

        <div className="h-[1px] bg-outline" />

        {/* 3. Древовидный список кампаний */}
        <div className="flex flex-col min-h-0">
          {isCollapsed ? (
            /* В свернутом виде: Поповер */
            <div className="group relative">
              <button
                type="button"
                className={`flex h-10 w-full items-center justify-center rounded-lg transition-all duration-150 ${
                  isCampaignActive
                    ? 'bg-[#5E44EB] text-white font-bold'
                    : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <svg
                  className="h-5 w-5 shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z"
                  />
                </svg>
              </button>

              <div className="absolute left-full top-0 z-50 ml-3 hidden w-72 rounded-2xl border border-outline bg-white p-3 shadow-lg group-hover:block">
                <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                  Ваши кампании Facebook
                </p>
                {isMeta ? (
                  <ul className="max-h-80 space-y-1 border-l border-gray-200 ml-4 pl-3">
                    {MOCK_CAMPAIGNS.map((campaign, index) => (
                      <li key={campaign.id}>
                        <CampaignNavItem
                          id={campaign.id}
                          name={campaign.name}
                          status={campaign.status}
                          isLast={index === MOCK_CAMPAIGNS.length - 1}
                        />
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="px-3 py-1 text-xs text-gray-400">
                    Инструмент в разработке
                  </p>
                )}
              </div>
            </div>
          ) : (
            /* В развернутом виде: Аккордеон с направляющей линией */
            <div className="flex flex-col min-h-0">
              <button
                type="button"
                onClick={() => setIsCampaignsOpen(!isCampaignsOpen)}
                className={`flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-sm font-semibold transition-all duration-150 ${
                  isCampaignActive
                    ? 'bg-[#5E44EB] text-white font-bold shadow-sm'
                    : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <div className="flex items-center gap-3">
                  <svg
                    className="h-5 w-5 shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z"
                    />
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z"
                    />
                  </svg>
                  <span>Кампании</span>
                </div>
                <svg
                  className={`h-4 w-4 text-current transition-transform duration-200 ${
                    isCampaignsOpen ? 'rotate-180' : ''
                  }`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2.5}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {isCampaignsOpen && (
                <div className="mt-3">
                  {isMeta ? (
                    <div className="flex flex-col">
                      <p className="mb-2 px-3 text-xs font-medium tracking-wide text-gray-400">
                        Ваши кампании Facebook
                      </p>
                      {/* Тонкая вертикальная серая линия-направляющая */}
                      <ul className="space-y-1 border-l border-gray-200 ml-5 pl-3 overflow-y-auto max-h-[40vh] pr-1">
                        {MOCK_CAMPAIGNS.map((campaign, index) => (
                          <li key={campaign.id}>
                            <CampaignNavItem
                              id={campaign.id}
                              name={campaign.name}
                              status={campaign.status}
                              isLast={index === MOCK_CAMPAIGNS.length - 1}
                            />
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    <div className="rounded-xl bg-gray-50 px-4 py-3 text-center border border-outline">
                      <p className="text-xs text-gray-400 leading-relaxed">
                        Кампании появятся после интеграции с этой платформой.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Аккаунты */}
        <ul className="space-y-1">
          <li>
            <NavLink
              to="/accounts"
              className={({ isActive }) =>
                [
                  'group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-semibold transition-all duration-150',
                  isActive
                    ? 'bg-[#5E44EB] text-white shadow-sm font-bold'
                    : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900',
                ].join(' ')
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <div className="absolute left-0 top-2.5 bottom-2.5 w-[4px] rounded-r-md bg-[#c2f913]" />
                  )}
                  <svg
                    className="h-5 w-5 shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                    />
                  </svg>
                  {!isCollapsed && <span>Аккаунты</span>}

                  {isCollapsed && (
                    <div className="absolute left-full top-1/2 z-50 ml-3 -translate-y-1/2 rounded-md bg-on-surface px-2.5 py-1.5 text-xs font-semibold text-surface opacity-0 shadow-md transition-opacity group-hover:opacity-100 pointer-events-none whitespace-nowrap">
                      Аккаунты
                    </div>
                  )}
                </>
              )}
            </NavLink>
          </li>
        </ul>
      </div>

      {/* Настройки */}
      <div className="shrink-0 border-t border-outline p-3">
        {/* Версия и надпись AI Analytics перенесены в самый низ */}
        {!isCollapsed && (
          <div className="flex flex-col px-3 py-2 mb-3 bg-gray-50 rounded-xl border border-outline/50">
            <span className="text-[9px] font-bold uppercase tracking-wider text-gray-400 leading-none">
              AI Analytics
            </span>
            <span className="mt-1 text-[10px] font-semibold text-gray-400 leading-none">
              v0.3.0
            </span>
          </div>
        )}

        <NavLink
          to="/settings"
          className={({ isActive }) =>
            [
              'group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-semibold transition-all duration-150',
              isActive
                ? 'bg-[#5E44EB] text-white shadow-sm font-bold'
                : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900',
            ].join(' ')
          }
        >
          {({ isActive }) => (
            <>
              {isActive && (
                <div className="absolute left-0 top-2.5 bottom-2.5 w-[4px] rounded-r-md bg-[#c2f913]" />
              )}
              <svg
                className="h-5 w-5 shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
              </svg>
              {!isCollapsed && <span>Настройки</span>}

              {isCollapsed && (
                <div className="absolute left-full top-1/2 z-50 ml-3 -translate-y-1/2 rounded-md bg-on-surface px-2.5 py-1.5 text-xs font-semibold text-surface opacity-0 shadow-md transition-opacity group-hover:opacity-100 pointer-events-none whitespace-nowrap">
                  Настройки
                </div>
              )}
            </>
          )}
        </NavLink>
      </div>
    </aside>
  );
}
