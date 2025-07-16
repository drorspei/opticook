import React, { useState, useEffect, useMemo } from 'react';
import useEmblaCarousel from 'embla-carousel-react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Session, ActiveTask } from '../types';
import { TaskCard } from './TaskCard';
import { getCurrentAI, getRemainingTime } from '../utils';

interface ChefTaskCarouselProps {
  session: Session;
  chefName: string;
  currentTime: number;
  onMarkDone: (chefName: string, instructionIndex: number) => void;
}

export const ChefTaskCarousel: React.FC<ChefTaskCarouselProps> = ({
  session,
  chefName,
  currentTime,
  onMarkDone,
}) => {
  // Get active tasks for this chef
  const activeTasks: ActiveTask[] = useMemo(() => {
    const chefTasks = session.cooking_map[chefName];
    if (!chefTasks) return [];
    return Object.values(chefTasks).sort((a, b) => a.instruction_index - b.instruction_index);
  }, [session, chefName]);

  const activeInstructionIndices = useMemo(() => activeTasks.map(t => t.instruction_index), [activeTasks]);

  const [emblaRef, emblaApi] = useEmblaCarousel({ loop: false, skipSnaps: false });
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [flashIndex, setFlashIndex] = useState<number | null>(null);
  const [urgentMessage, setUrgentMessage] = useState<string | null>(null);

  // Embla: update selected index on slide change
  useEffect(() => {
    if (!emblaApi) return;
    const onSelect = () => setSelectedIndex(emblaApi.selectedScrollSnap());
    emblaApi.on('select', onSelect);
    onSelect();
    return () => {
      emblaApi.off('select', onSelect);
    };
  }, [emblaApi]);

  // Embla: keyboard navigation (scoped to this carousel)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!emblaApi) return;
      if (e.key === 'ArrowLeft') emblaApi.scrollPrev();
      if (e.key === 'ArrowRight') emblaApi.scrollNext();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [emblaApi]);

  // Auto-advance and flash logic for this chef
  useEffect(() => {
    if (!emblaApi) return;
    const now = currentTime;
    let found = false;
    for (const activeTask of activeTasks) {
      const idx = activeTask.instruction_index;
      const currentAI = getCurrentAI(session, idx, activeTask.ai_index);
      const isNonAttention = currentAI && !currentAI.attention;
      const remaining = getRemainingTime(session, activeTask, now);
      if (isNonAttention && remaining === 0) {
        if (activeInstructionIndices[selectedIndex] !== idx) {
          const targetIdx = activeInstructionIndices.indexOf(idx);
          if (targetIdx !== -1) {
            emblaApi.scrollTo(targetIdx);
            setFlashIndex(idx);
            setUrgentMessage('Time to attend the task!');
            found = true;
            break;
          }
        } else {
          setFlashIndex(idx);
          setUrgentMessage('Time to attend the task!');
          found = true;
          break;
        }
      }
    }
    if (!found) {
      setFlashIndex(null);
      setUrgentMessage(null);
    }
    // eslint-disable-next-line
  }, [session, currentTime, emblaApi, activeInstructionIndices, selectedIndex, activeTasks]);

  if (activeInstructionIndices.length === 0) {
    return (
      <div className="mb-8">
        <h3 className="text-lg font-semibold mb-2">{chefName}</h3>
        <div className="w-full text-center text-gray-400 py-8">No active tasks</div>
      </div>
    );
  }

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-semibold">{chefName}</h3>
        <span className="text-sm text-gray-600">
          {selectedIndex + 1} / {activeInstructionIndices.length} tasks
        </span>
      </div>
      <div className="relative">
        <div className="overflow-hidden" ref={emblaRef}>
          <div className="flex">
            {activeInstructionIndices.map((instructionIndex) => (
              <div
                className="min-w-0 flex-[0_0_100%] px-2"
                key={instructionIndex}
                style={{ maxWidth: '100%' }}
              >
                <TaskCard
                  session={session}
                  instructionIndex={instructionIndex}
                  onMarkDone={() => onMarkDone(chefName, instructionIndex)}
                  currentTime={currentTime}
                  flash={flashIndex === instructionIndex}
                  urgentMessage={flashIndex === instructionIndex ? (urgentMessage ?? undefined) : undefined}
                />
              </div>
            ))}
          </div>
        </div>
        {activeInstructionIndices.length > 1 && (
          <>
            <button
              className="absolute left-0 top-1/2 -translate-y-1/2 z-10 embla-arrow"
              onClick={() => emblaApi && emblaApi.scrollPrev()}
              aria-label="Previous task"
              disabled={selectedIndex === 0}
            >
              <ChevronLeft className="w-6 h-6 text-gray-700" />
            </button>
            <button
              className="absolute right-0 top-1/2 -translate-y-1/2 z-10 embla-arrow"
              onClick={() => emblaApi && emblaApi.scrollNext()}
              aria-label="Next task"
              disabled={selectedIndex === activeInstructionIndices.length - 1}
            >
              <ChevronRight className="w-6 h-6 text-gray-700" />
            </button>
          </>
        )}
      </div>
    </div>
  );
}; 