import AdPreviewCard from './AdPreviewCard';
import { collectCampaignAds } from '../../utils/campaignVerdict';

/**
 * Список объявлений кампании с опциональным фильтром по группе.
 */
export default function CampaignAllAdsView({ adSets, resultLabel, filterAdSetId = null, currency = 'KZT' }) {
  const adsWithGroup = collectCampaignAds(adSets, filterAdSetId);

  if (adsWithGroup.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-outline bg-white p-8 text-center">
        <p className="text-sm text-gray-400">
          {filterAdSetId
            ? 'В этой группе пока нет объявлений.'
            : 'В этой кампании пока нет объявлений.'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {adsWithGroup.map((ad) => (
        <AdPreviewCard
          key={ad.id}
          ad={ad}
          resultLabel={resultLabel}
          adSetName={ad.adSetName}
          currency={currency}
        />
      ))}
    </div>
  );
}
