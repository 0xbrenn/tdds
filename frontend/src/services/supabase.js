import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

export const badgeService = {
  async registerUser(email) {
    const { data, error } = await supabase
      .from('users')
      .insert([
        {
          email,
          progress: { email: true, twitter: false, telegram: false, discord: false, tweet: false },
          created_at: new Date().toISOString()
        }
      ])
      .select()
      .single();
    
    if (error) throw error;
    return data;
  },

  async updateTaskProgress(email, taskName) {
    const { data: user, error: fetchError } = await supabase
      .from('users')
      .select('progress')
      .eq('email', email)
      .single();
    
    if (fetchError) throw fetchError;
    
    const updatedProgress = { ...user.progress, [taskName]: true };
    
    const { data, error } = await supabase
      .from('users')
      .update({ progress: updatedProgress })
      .eq('email', email)
      .select()
      .single();
    
    if (error) throw error;
    return data;
  },

  async verifyTwitter(email, handle) {
    const { data, error } = await supabase
      .from('users')
      .update({ 
        x_handle: handle,
        progress: supabase.rpc('update_progress_field', { field: 'twitter', value: true })
      })
      .eq('email', email);
    
    if (error) throw error;
    return data;
  },

  async verifyTelegram(email, username) {
    const { data, error } = await supabase
      .from('users')
      .update({ 
        telegram_username: username,
        progress: supabase.rpc('update_progress_field', { field: 'telegram', value: true })
      })
      .eq('email', email);
    
    if (error) throw error;
    return data;
  },

  async verifyDiscord(email, discordId) {
    const { data, error } = await supabase
      .from('users')
      .update({ 
        discord_id: discordId,
        progress: supabase.rpc('update_progress_field', { field: 'discord', value: true })
      })
      .eq('email', email);
    
    if (error) throw error;
    return data;
  },

  async submitTweet(email, tweetUrl) {
    const { data, error } = await supabase
      .from('users')
      .update({ 
        tweet_link: tweetUrl,
        progress: supabase.rpc('update_progress_field', { field: 'tweet', value: true })
      })
      .eq('email', email);
    
    if (error) throw error;
    return data;
  },

  async claimBadge(email) {
    const { data, error } = await supabase
      .from('users')
      .update({ 
        badge_claimed: true,
        claimed_at: new Date().toISOString()
      })
      .eq('email', email)
      .select()
      .single();
    
    if (error) throw error;
    return data;
  }
};