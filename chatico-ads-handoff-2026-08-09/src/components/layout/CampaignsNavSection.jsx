import { Link, NavLink, useLocation } from 'react-router-dom';
import { MOCK_CAMPAIGNS, getSidebarCampaigns, SIDEBAR_CAMPAIGN_LIMIT } from '../../data/mockCampaigns';
import { campaignPath, parseCampaignLocation } from '../../utils/campaignNav';

const CAMPAIGN_COUNT = MOCK_CAMPAIGNS.length;
const SHOW_ALL_LINK = CAMPAIGN_COUNT > SIDEBAR_CAMPAIGN_LIMIT;

function StatusDot({ status, active }) {
  const paused = status === 'paused';
  return (
    <span
      className={`h-1.5 w-1.5 shrink-0 rounded-full ${
        paused
          ? active
            ? 'bg-white/60'
            : 'bg-gray-400'
          : active
            ? 'bg-[#c2f913]'
            : 'bg-[#5a9c34]'
      }`}
    />
  );
}

function CampaignNavItem({ campaign, isActive, compact = false, to }) {
  const label = campaign.shortName ?? campaign.name;

  if (compact) {
    return (
      <NavLink
        to={to}
        title={campaign.name}
        className={() =>
          [
            'flex min-w-0 items-center gap-2 rounded-md py-1.5 pl-2 pr-2 text-xs font-medium transition-colors',
            isActive
              ? 'bg-[#5E44EB] font-bold text-white shadow-sm'
              : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
          ].join(' ')
        }
      >
        <StatusDot status={campaign.status} active={isActive} />
        <span className="truncate">{label}</span>
      </NavLink>
    );
  }

  return (
    <NavLink
      to={to}
      title={campaign.name}
      className={() =>
        [
          'group relative flex min-w-0 items-center gap-2 rounded-lg py-2 pl-3 pr-3 text-sm font-medium transition-all duration-150',
          isActive
            ? 'bg-[#5E44EB] font-bold text-white shadow-sm'
            : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900',
        ].join(' ')
      }
    >
      {isActive && (
        <div className="absolute left-0 top-2 bottom-2 w-[4px] rounded-r-md bg-[#c2f913]" />
      )}
      <StatusDot status={campaign.status} active={isActive} />
      <span className="truncate">{label}</span>
    </NavLink>
  );
}

function AllCampaignsNavItem({ isActive, compact = false }) {
  if (compact) {
    return (
      <NavLink
        to="/campaigns"
        className={() =>
          [
            'flex min-w-0 items-center rounded-md py-1.5 pl-2 pr-2 text-xs font-medium transition-colors',
            isActive
              ? 'bg-[#5E44EB] font-bold text-white shadow-sm'
              : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
          ].join(' ')
        }
      >
        <span className="truncate">Все кампании</span>
      </NavLink>
    );
  }

  return (
    <NavLink
      to="/campaigns"
      className={() =>
        [
          'group relative flex min-w-0 items-center rounded-lg py-2 pl-3 pr-3 text-sm font-medium transition-all duration-150',
          isActive
            ? 'bg-[#5E44EB] font-bold text-white shadow-sm'
            : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900',
        ].join(' ')
      }
    >
      {isActive && (
        <div className="absolute left-0 top-2 bottom-2 w-[4px] rounded-r-md bg-[#c2f913]" />
      )}
      <span className="truncate">Все кампании</span>
    </NavLink>
  );
}

/**
 * Sidebar: Рекламные кампании + плоский список кампаний.
 */
export default function CampaignsNavSection({ isCollapsed }) {
  const location = useLocation();
  const isAdsSection = location.pathname.startsWith('/campaigns');
  const isAllCampaignsPage = location.pathname === '/campaigns';
  const { campaignId } = parseCampaignLocation(location.pathname, location.search);

  const label = `Рекламные кампании · ${CAMPAIGN_COUNT}`;
  const sidebarCampaigns = getSidebarCampaigns(SIDEBAR_CAMPAIGN_LIMIT);

  const renderCampaignList = (compact = false) => (
    <ul className={`space-y-0.5 ${compact ? '' : 'relative ml-2 mt-1 border-l border-gray-200 pl-1'}`}>
      {sidebarCampaigns.map((campaign) => (
        <li key={campaign.id}>
          <CampaignNavItem
            campaign={campaign}
            isActive={campaignId === campaign.id}
            compact={compact}
            to={campaignPath(campaign.id)}
          />
        </li>
      ))}
      {SHOW_ALL_LINK && (
        <li>
          <AllCampaignsNavItem isActive={isAllCampaignsPage} compact={compact} />
        </li>
      )}
    </ul>
  );

  if (isCollapsed) {
    return (
      <div className="group relative">
        <NavLink
          to="/campaigns"
          className={() =>
            [
              'relative flex items-center justify-center rounded-lg px-3 py-2.5 transition-all duration-150',
              isAdsSection
                ? 'bg-[#5E44EB] text-white shadow-sm'
                : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900',
            ].join(' ')
          }
        >
          {isAdsSection && (
            <div className="absolute left-0 top-2.5 bottom-2.5 w-[4px] rounded-r-md bg-[#c2f913]" />
          )}
          <svg className="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" />
          </svg>
          <div className="pointer-events-none absolute left-full top-1/2 z-50 ml-3 -translate-y-1/2 whitespace-nowrap rounded-md bg-on-surface px-2.5 py-1.5 text-xs font-semibold text-surface opacity-0 shadow-md transition-opacity group-hover:opacity-100">
            {label}
          </div>
        </NavLink>
        <div className="absolute left-full top-0 z-50 ml-3 hidden max-h-[70vh] w-64 overflow-y-auto rounded-xl border border-outline bg-white p-2 shadow-lg group-hover:block">
          <p className="mb-2 px-2 text-[10px] font-bold uppercase tracking-wider text-gray-400">{label}</p>
          {renderCampaignList(true)}
        </div>
      </div>
    );
  }

  return (
    <div>
      <Link
        to="/campaigns"
        className={[
          'group relative flex min-w-0 items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-semibold transition-all duration-150',
          isAdsSection
            ? 'bg-[#5E44EB] font-bold text-white shadow-sm'
            : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900',
        ].join(' ')}
      >
        {isAdsSection && (
          <div className="absolute left-0 top-2.5 bottom-2.5 w-[4px] rounded-r-md bg-[#c2f913]" />
        )}
        <svg className="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" />
        </svg>
        <span className="truncate">{label}</span>
      </Link>

      {renderCampaignList()}
    </div>
  );
}
