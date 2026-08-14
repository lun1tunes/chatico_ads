/** Навигация: кампания → группа / все объявления. */
export function campaignPath(campaignId, { adSetId } = {}) {
  if (adSetId) {
    return `/campaigns/${campaignId}?adSet=${adSetId}`;
  }
  return `/campaigns/${campaignId}`;
}

/** Страница всех объявлений кампании. Фильтр группы — query `adSet`. */
export function campaignAdsPath(campaignId, { adSetId } = {}) {
  if (adSetId) {
    return `/campaigns/${campaignId}/ads?adSet=${adSetId}`;
  }
  return `/campaigns/${campaignId}/ads`;
}

export function parseCampaignLocation(pathname, search = '') {
  const adsMatch = pathname.match(/^\/campaigns\/([^/]+)\/ads\/?$/);
  const campaignMatch = pathname.match(/^\/campaigns\/([^/]+)/);
  const campaignId = adsMatch?.[1] ?? campaignMatch?.[1] ?? null;
  const params = new URLSearchParams(search);
  const isAdsPage = Boolean(adsMatch);

  return {
    campaignId,
    adSetId: params.get('adSet'),
    isAdsPage,
    /** @deprecated legacy query; редирект на /ads */
    view: params.get('view'),
  };
}

/** Якорь блока «Группы объявлений» на странице кампании. */
export const CAMPAIGN_AD_GROUPS_ANCHOR = 'ad-groups';

export function campaignAdGroupsPath(campaignId) {
  return `${campaignPath(campaignId)}#${CAMPAIGN_AD_GROUPS_ANCHOR}`;
}

export function getCampaignAdsCount(campaign) {
  return (campaign?.adSets ?? []).reduce((sum, s) => sum + (s.ads?.length ?? 0), 0);
}

export function campaignHasAdsView(campaign) {
  return Boolean(campaign?.metrics) && getCampaignAdsCount(campaign) > 0;
}
